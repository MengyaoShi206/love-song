from django.core.management.base import BaseCommand
from api.storage_example import storage_example

class Command(BaseCommand):
    help = '测试分布式存储系统'
    
    def handle(self, *args, **options):
        self.stdout.write('开始测试分布式存储系统...')
        storage_example()
        self.stdout.write(self.style.SUCCESS('存储系统测试完成'))