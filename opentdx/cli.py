import click
from opentdx.commands.doc_demo import run_interactive
from opentdx.commands import run_market_monitor


@click.group()
def cli():
    """OpenTDX - TDX stock data client CLI"""
    pass


@cli.command()
def doc():
    """交互式接口文档"""
    run_interactive()


@cli.command(name='mm')
@click.option('--search', default='', help='搜索关键词（匹配代码、名称或异动描述）')
@click.option('--interval', default=3, help='查询间隔（秒），默认3秒')
@click.option('--count', default=1000, help='每个市场获取的监控记录数，默认1000条')
@click.option('--split/--no-split', default=False, help='是否使用分隔符显示')
def market_monitor(interval, count, split, search):
    """实时监控市场异动数据（每3秒刷新）

    同时保存到 log 文件

    使用 tee 命令保存日志(不支持color显示)
    opentdx mm | tee /tmp/monitor_log.txt
    """
    run_market_monitor(interval=interval, count=count, split=split, search=search)


if __name__ == '__main__':
    cli()
