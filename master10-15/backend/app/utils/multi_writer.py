# backend/app/utils/multi_writer.py
"""
多库写入工具：
- 主库（SessionMain）同步写入
- Doris 分析库（SessionDoris）异步镜像写入
- 行为日志类表支持批量异步队列写入
"""

import asyncio
import threading
from datetime import datetime
from typing import Any
from app.database import SessionLocal, SessionDoris
from sqlalchemy.orm import object_mapper

# ================ 主类：MultiWriter ================
class MultiWriter:
    """
    主库同步 + Doris 异步镜像写入封装
    用法：
        from app.utils.multi_writer import MultiWriter
        MultiWriter.write(user_instance)
    """

    @staticmethod
    def write(model_instance: Any, db=None, mirror: bool = True):
        """
        同步写主库，可复用外部 Session（例如 FastAPI 的 db）
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            db.add(model_instance)
            db.commit()
            db.refresh(model_instance)
        except Exception as e:
            db.rollback()
            print(f"[MultiWriter] 主库写入失败: {e}")
            raise
        finally:
            if own_session:
                db.close()

        # 异步镜像写入 Doris
        if mirror and SessionDoris is not None:
            async def runner():
                await MultiWriter._async_mirror(model_instance)

            try:
                # 如果当前线程已有事件循环（异步环境）
                loop = asyncio.get_running_loop()
                loop.create_task(runner())
            except RuntimeError:
                # 若当前线程无事件循环（同步环境/FastAPI def）
                threading.Thread(target=lambda: asyncio.run(runner())).start()

        return model_instance

    @staticmethod
    async def _async_mirror(instance: Any):
        """异步镜像写入 Doris（不阻塞主业务）"""
        if SessionDoris is None:
            return
        try:
            # 提取 instance 数据为纯字典
            mapper = object_mapper(instance)
            data = {col.key: getattr(instance, col.key) for col in mapper.columns}

            # 创建同类的新对象（防止 Session 冲突）
            cls = type(instance)
            detached = cls(**data)

            db = SessionDoris()
            db.add(detached)
            db.commit()
            db.close()
            print(f"[MultiWriter] 已异步镜像写入 Doris: {cls.__tablename__}")
        except Exception as e:
            print(f"[WARN] Doris 异步写入失败: {e}")


# ================ 队列类：DorisQueue（批量异步写）================
class DorisQueue:
    """
    用于行为日志、埋点事件等高频数据。
    异步队列批量刷入 Doris，每秒写一次，每次最多 100 条。
    用法：
        await DorisQueue.add(record)
    """

    _queue = asyncio.Queue()
    _started = False

    @classmethod
    async def worker(cls):
        """后台常驻任务：定期批量提交队列"""
        if SessionDoris is None:
            print("[DorisQueue] Doris 未配置，队列关闭。")
            return

        print("[DorisQueue] 后台异步写入任务已启动。")
        while True:
            batch = []
            try:
                while not cls._queue.empty() and len(batch) < 100:
                    batch.append(await cls._queue.get())

                if batch:
                    db = SessionDoris()
                    # 同样进行复制防止跨 Session
                    safe_batch = []
                    for inst in batch:
                        mapper = object_mapper(inst)
                        data = {col.key: getattr(inst, col.key) for col in mapper.columns}
                        cls_ = type(inst)
                        safe_batch.append(cls_(**data))

                    db.add_all(safe_batch)
                    db.commit()
                    db.close()
                    print(f"[DorisQueue] ✅ 批量写入 {len(safe_batch)} 条记录到 Doris。")
            except Exception as e:
                print(f"[DorisQueue] 批量写入异常: {e}")

            await asyncio.sleep(1)  # 每秒刷新一次

    @classmethod
    def start(cls):
        """在 FastAPI 启动事件中调用"""
        if not cls._started:
            asyncio.create_task(cls.worker())
            cls._started = True

    @classmethod
    async def add(cls, record: Any):
        """将一条记录加入队列"""
        await cls._queue.put(record)
