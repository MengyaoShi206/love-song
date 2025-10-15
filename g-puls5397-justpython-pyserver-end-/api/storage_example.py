from .storage import StorageManager, RabbitMQClient, ElasticsearchClient, ClickHouseClient
import logging

# 配置日志
logger = logging.getLogger(__name__)

def storage_example():
    """
    存储系统使用示例
    """
    # 检查是否使用分布式存储
    if not StorageManager.is_distributed_storage():
        logger.info("当前使用SQLite存储，分布式存储示例将不可用")
        return
    
    # 示例数据
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'profile': {
            'age': 30,
            'gender': 'male',
            'interests': ['programming', 'reading']
        }
    }
    
    # 使用RabbitMQ进行临时存储
    rabbitmq_example(user_data)
    
    # 使用Elasticsearch进行缓存
    elasticsearch_example(user_data)
    
    # 使用ClickHouse进行长期存储
    clickhouse_example(user_data)

def rabbitmq_example(data):
    """
    RabbitMQ使用示例
    """
    try:
        # 初始化RabbitMQ客户端
        client = RabbitMQClient()
        
        # 发布消息
        queue_name = 'user_events'
        success = client.publish(queue_name, {
            'event': 'user_created',
            'data': data
        })
        
        if success:
            logger.info(f"成功发布消息到RabbitMQ队列: {queue_name}")
        else:
            logger.error(f"发布消息到RabbitMQ队列失败: {queue_name}")
        
        # 关闭连接
        client.close()
    except Exception as e:
        logger.error(f"RabbitMQ示例执行失败: {str(e)}")

def elasticsearch_example(data):
    """
    Elasticsearch使用示例
    """
    try:
        # 初始化Elasticsearch客户端
        client = ElasticsearchClient()
        
        # 索引文档
        index_name = 'users'
        doc_id = data['username']
        success = client.index(index_name, doc_id, data)
        
        if success:
            logger.info(f"成功索引文档到Elasticsearch: {index_name}/{doc_id}")
            
            # 搜索文档
            search_query = {
                'query': {
                    'match': {
                        'username': data['username']
                    }
                }
            }
            results = client.search(index_name, search_query)
            logger.info(f"Elasticsearch搜索结果: {results}")
            
            # 获取文档
            doc = client.get(index_name, doc_id)
            logger.info(f"Elasticsearch获取文档: {doc}")
            
            # 删除文档
            success = client.delete(index_name, doc_id)
            if success:
                logger.info(f"成功从Elasticsearch删除文档: {index_name}/{doc_id}")
            else:
                logger.error(f"从Elasticsearch删除文档失败: {index_name}/{doc_id}")
        else:
            logger.error(f"索引文档到Elasticsearch失败: {index_name}/{doc_id}")
    except Exception as e:
        logger.error(f"Elasticsearch示例执行失败: {str(e)}")

def clickhouse_example(data):
    """
    ClickHouse使用示例
    """
    try:
        # 初始化ClickHouse客户端
        client = ClickHouseClient()
        
        # 创建表（如果不存在）
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            username String,
            email String,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (username, created_at)
        """
        client.execute(create_table_query)
        
        # 插入数据
        table_name = 'users'
        insert_data = {
            'username': data['username'],
            'email': data['email']
        }
        success = client.insert(table_name, insert_data)
        
        if success:
            logger.info(f"成功插入数据到ClickHouse表: {table_name}")
            
            # 查询数据
            query = f"SELECT * FROM {table_name} WHERE username = %(username)s"
            params = {'username': data['username']}
            results = client.execute(query, params)
            logger.info(f"ClickHouse查询结果: {results}")
        else:
            logger.error(f"插入数据到ClickHouse表失败: {table_name}")
    except Exception as e:
        logger.error(f"ClickHouse示例执行失败: {str(e)}")

# 在Django应用中使用示例
# 可以在视图或命令中调用storage_example()函数
"""
# 在视图中使用示例
from django.http import JsonResponse

def storage_test_view(request):
    storage_example()
    return JsonResponse({'status': 'success', 'message': '存储系统测试完成'})

# 在Django命令中使用示例
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = '测试分布式存储系统'
    
    def handle(self, *args, **options):
        storage_example()
        self.stdout.write(self.style.SUCCESS('存储系统测试完成'))
"""