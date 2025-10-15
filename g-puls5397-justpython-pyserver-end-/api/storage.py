import json
import logging
from django.conf import settings

# 配置日志
logger = logging.getLogger(__name__)

class StorageManager:
    """
    存储管理器，用于处理不同存储系统的数据操作
    """
    
    @staticmethod
    def get_storage_type():
        """
        获取当前使用的存储类型
        """
        return getattr(settings, 'DB_TYPE', 'sqlite')
    
    @staticmethod
    def is_distributed_storage():
        """
        检查是否使用分布式存储
        """
        return StorageManager.get_storage_type() != 'sqlite'


class RabbitMQClient:
    """
    RabbitMQ客户端，用于临时存储
    """
    
    def __init__(self):
        """
        初始化RabbitMQ客户端
        """
        if not StorageManager.is_distributed_storage():
            logger.warning("未启用分布式存储，RabbitMQ客户端将不可用")
            return
        
        try:
            import pika
            
            # 获取RabbitMQ配置
            config = settings.RABBITMQ
            credentials = pika.PlainCredentials(config['USER'], config['PASSWORD'])
            parameters = pika.ConnectionParameters(
                host=config['HOST'],
                port=config['PORT'],
                virtual_host=config['VIRTUAL_HOST'],
                credentials=credentials
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info("RabbitMQ客户端初始化成功")
        except ImportError:
            logger.error("未安装pika库，无法使用RabbitMQ")
            self.connection = None
            self.channel = None
        except Exception as e:
            logger.error(f"RabbitMQ客户端初始化失败: {str(e)}")
            self.connection = None
            self.channel = None
    
    def publish(self, queue, message):
        """
        发布消息到队列
        """
        if not self.channel:
            logger.error("RabbitMQ客户端未初始化，无法发布消息")
            return False
        
        try:
            # 确保队列存在
            self.channel.queue_declare(queue=queue, durable=True)
            
            # 发布消息
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message) if isinstance(message, (dict, list)) else str(message),
                properties=pika.BasicProperties(delivery_mode=2)  # 消息持久化
            )
            return True
        except Exception as e:
            logger.error(f"发布消息到RabbitMQ失败: {str(e)}")
            return False
    
    def consume(self, queue, callback):
        """
        从队列消费消息
        """
        if not self.channel:
            logger.error("RabbitMQ客户端未初始化，无法消费消息")
            return False
        
        try:
            # 确保队列存在
            self.channel.queue_declare(queue=queue, durable=True)
            
            # 设置每次只接收一条消息
            self.channel.basic_qos(prefetch_count=1)
            
            # 消费消息
            self.channel.basic_consume(queue=queue, on_message_callback=callback)
            
            # 开始消费
            self.channel.start_consuming()
            return True
        except Exception as e:
            logger.error(f"从RabbitMQ消费消息失败: {str(e)}")
            return False
    
    def close(self):
        """
        关闭连接
        """
        if self.connection:
            self.connection.close()


class ElasticsearchClient:
    """
    Elasticsearch客户端，用于缓存
    """
    
    def __init__(self):
        """
        初始化Elasticsearch客户端
        """
        if not StorageManager.is_distributed_storage():
            logger.warning("未启用分布式存储，Elasticsearch客户端将不可用")
            return
        
        try:
            from elasticsearch import Elasticsearch
            
            # 获取Elasticsearch配置
            config = settings.ELASTICSEARCH
            auth = None
            if config['USER'] and config['PASSWORD']:
                auth = (config['USER'], config['PASSWORD'])
            
            self.es = Elasticsearch(
                [f"{config['HOST']}:{config['PORT']}"],
                http_auth=auth
            )
            self.index_prefix = config['INDEX_PREFIX']
            logger.info("Elasticsearch客户端初始化成功")
        except ImportError:
            logger.error("未安装elasticsearch库，无法使用Elasticsearch")
            self.es = None
        except Exception as e:
            logger.error(f"Elasticsearch客户端初始化失败: {str(e)}")
            self.es = None
    
    def index(self, index, doc_id, document):
        """
        索引文档
        """
        if not self.es:
            logger.error("Elasticsearch客户端未初始化，无法索引文档")
            return False
        
        try:
            # 添加前缀到索引名
            index_name = f"{self.index_prefix}{index}"
            
            # 索引文档
            self.es.index(index=index_name, id=doc_id, body=document)
            return True
        except Exception as e:
            logger.error(f"索引文档到Elasticsearch失败: {str(e)}")
            return False
    
    def search(self, index, query):
        """
        搜索文档
        """
        if not self.es:
            logger.error("Elasticsearch客户端未初始化，无法搜索文档")
            return []
        
        try:
            # 添加前缀到索引名
            index_name = f"{self.index_prefix}{index}"
            
            # 搜索文档
            result = self.es.search(index=index_name, body=query)
            return result['hits']['hits']
        except Exception as e:
            logger.error(f"从Elasticsearch搜索文档失败: {str(e)}")
            return []
    
    def get(self, index, doc_id):
        """
        获取文档
        """
        if not self.es:
            logger.error("Elasticsearch客户端未初始化，无法获取文档")
            return None
        
        try:
            # 添加前缀到索引名
            index_name = f"{self.index_prefix}{index}"
            
            # 获取文档
            result = self.es.get(index=index_name, id=doc_id)
            return result['_source']
        except Exception as e:
            logger.error(f"从Elasticsearch获取文档失败: {str(e)}")
            return None
    
    def delete(self, index, doc_id):
        """
        删除文档
        """
        if not self.es:
            logger.error("Elasticsearch客户端未初始化，无法删除文档")
            return False
        
        try:
            # 添加前缀到索引名
            index_name = f"{self.index_prefix}{index}"
            
            # 删除文档
            self.es.delete(index=index_name, id=doc_id)
            return True
        except Exception as e:
            logger.error(f"从Elasticsearch删除文档失败: {str(e)}")
            return False


class ClickHouseClient:
    """
    ClickHouse客户端，用于长期存储
    """
    
    def __init__(self):
        """
        初始化ClickHouse客户端
        """
        if not StorageManager.is_distributed_storage():
            logger.warning("未启用分布式存储，ClickHouse客户端将不可用")
            return
        
        try:
            from clickhouse_driver import Client
            
            # 获取ClickHouse配置
            config = settings.CLICKHOUSE
            
            self.client = Client(
                host=config['HOST'],
                port=config['PORT'],
                user=config['USER'],
                password=config['PASSWORD'],
                database=config['DATABASE']
            )
            logger.info("ClickHouse客户端初始化成功")
        except ImportError:
            logger.error("未安装clickhouse_driver库，无法使用ClickHouse")
            self.client = None
        except Exception as e:
            logger.error(f"ClickHouse客户端初始化失败: {str(e)}")
            self.client = None
    
    def execute(self, query, params=None):
        """
        执行SQL查询
        """
        if not self.client:
            logger.error("ClickHouse客户端未初始化，无法执行查询")
            return None
        
        try:
            # 执行查询
            result = self.client.execute(query, params or {})
            return result
        except Exception as e:
            logger.error(f"执行ClickHouse查询失败: {str(e)}")
            return None
    
    def insert(self, table, data):
        """
        插入数据
        """
        if not self.client or not data:
            logger.error("ClickHouse客户端未初始化或数据为空，无法插入数据")
            return False
        
        try:
            # 获取列名
            columns = list(data[0].keys()) if isinstance(data, list) else list(data.keys())
            
            # 准备SQL
            columns_str = ", ".join(columns)
            placeholders = ", ".join([f":{col}" for col in columns])
            query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            
            # 执行插入
            if isinstance(data, list):
                self.client.execute(query, data)
            else:
                self.client.execute(query, [data])
            return True
        except Exception as e:
            logger.error(f"插入数据到ClickHouse失败: {str(e)}")
            return False