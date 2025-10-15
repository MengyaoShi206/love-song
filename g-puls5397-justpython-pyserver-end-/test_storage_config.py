import os
import sys
import configparser
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def test_config():
    """
    测试配置文件是否存在并且可以正确读取
    """
    config_path = os.path.join(BASE_DIR, 'config.ini')
    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        return False
    
    try:
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        # 检查必要的配置项
        required_sections = ['database', 'sqlite', 'rabbitmq', 'elasticsearch', 'clickhouse']
        for section in required_sections:
            if section not in config:
                logger.error(f"配置文件缺少必要的部分: {section}")
                return False
        
        # 获取数据库类型
        db_type = config.get('database', 'type', fallback='sqlite')
        logger.info(f"当前配置的数据库类型: {db_type}")
        
        # 检查SQLite配置
        sqlite_name = config.get('sqlite', 'name', fallback='db.sqlite3')
        sqlite_path = os.path.join(BASE_DIR, sqlite_name)
        logger.info(f"SQLite数据库路径: {sqlite_path}")
        
        # 如果使用分布式存储，检查相关配置
        if db_type == 'distributed':
            # 检查RabbitMQ配置
            rabbitmq_host = config.get('rabbitmq', 'host', fallback='localhost')
            rabbitmq_port = config.getint('rabbitmq', 'port', fallback=5672)
            logger.info(f"RabbitMQ配置: {rabbitmq_host}:{rabbitmq_port}")
            
            # 检查Elasticsearch配置
            es_host = config.get('elasticsearch', 'host', fallback='localhost')
            es_port = config.getint('elasticsearch', 'port', fallback=9200)
            logger.info(f"Elasticsearch配置: {es_host}:{es_port}")
            
            # 检查ClickHouse配置
            ch_host = config.get('clickhouse', 'host', fallback='localhost')
            ch_port = config.getint('clickhouse', 'port', fallback=9000)
            logger.info(f"ClickHouse配置: {ch_host}:{ch_port}")
        
        logger.info("配置文件检查通过")
        return True
    except Exception as e:
        logger.error(f"读取配置文件失败: {str(e)}")
        return False

def test_dependencies():
    """
    测试是否安装了必要的依赖
    """
    dependencies = {
        'pika': '用于连接RabbitMQ',
        'elasticsearch': '用于连接Elasticsearch',
        'clickhouse_driver': '用于连接ClickHouse'
    }
    
    missing_deps = []
    for dep, desc in dependencies.items():
        try:
            __import__(dep)
            logger.info(f"依赖已安装: {dep} ({desc})")
        except ImportError:
            logger.warning(f"依赖未安装: {dep} ({desc})")
            missing_deps.append(dep)
    
    if missing_deps:
        logger.warning(f"缺少以下依赖: {', '.join(missing_deps)}")
        logger.warning("请使用以下命令安装缺少的依赖:")
        logger.warning(f"pip install {' '.join(missing_deps)}")
        return False
    
    logger.info("所有依赖检查通过")
    return True

def test_connections():
    """
    测试与各存储系统的连接
    """
    # 读取配置
    config = configparser.ConfigParser()
    config_path = os.path.join(BASE_DIR, 'config.ini')
    config.read(config_path, encoding='utf-8')
    
    db_type = config.get('database', 'type', fallback='sqlite')
    if db_type != 'distributed':
        logger.info("当前未配置为分布式存储，跳过连接测试")
        return True
    
    # 测试RabbitMQ连接
    try:
        import pika
        rabbitmq_host = config.get('rabbitmq', 'host', fallback='localhost')
        rabbitmq_port = config.getint('rabbitmq', 'port', fallback=5672)
        rabbitmq_user = config.get('rabbitmq', 'user', fallback='guest')
        rabbitmq_password = config.get('rabbitmq', 'password', fallback='guest')
        rabbitmq_vhost = config.get('rabbitmq', 'virtual_host', fallback='/')
        
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
        parameters = pika.ConnectionParameters(
            host=rabbitmq_host,
            port=rabbitmq_port,
            virtual_host=rabbitmq_vhost,
            credentials=credentials
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        connection.close()
        
        logger.info("RabbitMQ连接测试通过")
    except ImportError:
        logger.warning("未安装pika库，无法测试RabbitMQ连接")
    except Exception as e:
        logger.error(f"RabbitMQ连接测试失败: {str(e)}")
        return False
    
    # 测试Elasticsearch连接
    try:
        from elasticsearch import Elasticsearch
        es_host = config.get('elasticsearch', 'host', fallback='localhost')
        es_port = config.getint('elasticsearch', 'port', fallback=9200)
        es_user = config.get('elasticsearch', 'user', fallback='')
        es_password = config.get('elasticsearch', 'password', fallback='')
        
        auth = None
        if es_user and es_password:
            auth = (es_user, es_password)
        
        es = Elasticsearch(
            [f"{es_host}:{es_port}"],
            http_auth=auth
        )
        
        if es.ping():
            logger.info("Elasticsearch连接测试通过")
        else:
            logger.error("Elasticsearch连接测试失败: 无法ping通服务器")
            return False
    except ImportError:
        logger.warning("未安装elasticsearch库，无法测试Elasticsearch连接")
    except Exception as e:
        logger.error(f"Elasticsearch连接测试失败: {str(e)}")
        return False
    
    # 测试ClickHouse连接
    try:
        from clickhouse_driver import Client
        ch_host = config.get('clickhouse', 'host', fallback='localhost')
        ch_port = config.getint('clickhouse', 'port', fallback=9000)
        ch_user = config.get('clickhouse', 'user', fallback='default')
        ch_password = config.get('clickhouse', 'password', fallback='')
        ch_database = config.get('clickhouse', 'database', fallback='pyserver')
        
        client = Client(
            host=ch_host,
            port=ch_port,
            user=ch_user,
            password=ch_password,
            database=ch_database
        )
        
        # 执行简单查询测试连接
        result = client.execute('SELECT 1')
        if result and result[0][0] == 1:
            logger.info("ClickHouse连接测试通过")
        else:
            logger.error("ClickHouse连接测试失败: 查询结果异常")
            return False
    except ImportError:
        logger.warning("未安装clickhouse_driver库，无法测试ClickHouse连接")
    except Exception as e:
        logger.error(f"ClickHouse连接测试失败: {str(e)}")
        return False
    
    logger.info("所有连接测试通过")
    return True

def main():
    """
    主函数
    """
    logger.info("开始测试存储配置...")
    
    # 测试配置文件
    if not test_config():
        logger.error("配置文件测试失败")
        return 1
    
    # 测试依赖
    test_dependencies()
    
    # 测试连接
    if not test_connections():
        logger.error("连接测试失败")
        return 1
    
    logger.info("存储配置测试完成")
    return 0

if __name__ == '__main__':
    sys.exit(main())