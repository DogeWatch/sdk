#!/usr/bin/env python
import binaryai
from binaryai.client import Client
from binaryai.function import query_function, create_function_set, query_function_set
import subprocess
import platform
import click
import json
import os

# diff between py2 and py3
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


def get_user_idadir():
    system = platform.system()
    if system == 'Windows':
        return os.path.join(os.getenv('APPDATA'), "Hex-Rays", "IDA Pro")
    elif system in ['Linux', 'Darwin']:
        return os.path.join(os.getenv('HOME'), ".idapro")
    else:
        return ""


def get_plugin_path():
    return os.path.join(os.path.abspath(os.path.join(binaryai.__file__, os.path.pardir)), "ida_binaryai.py")


@click.group(invoke_without_command=True)
@click.option('--help', '-h', is_flag=True, help='show this message and exit.')
@click.option('--version', '-v', is_flag=True, help='show version')
@click.pass_context
def cli(ctx, help, version):
    if ctx.invoked_subcommand is None or help:
        if version:
            click.echo(binaryai.__version__)
            ctx.exit()
        else:
            banner = r'''
 ____  _                           _    ___
| __ )(_)_ __   __ _ _ __ _   _   / \  |_ _|
|  _ \| | '_ \ / _` | '__| | | | / _ \  | |
| |_) | | | | | (_| | |  | |_| |/ ___ \ | |
|____/|_|_| |_|\__,_|_|   \__, /_/   \_\___|
                          |___/
        '''
            click.echo(banner)
            click.echo(ctx.get_help())
            ctx.exit()


@cli.command('install_ida_plugin', short_help='install IDA plugin')
@click.option('--directory', '-d', help='IDA plugin directory', type=click.Path(), default=None)
@click.pass_context
def InstallPlugin(ctx, directory):
    if directory and not os.path.isdir(directory):
        click.echo('Invalid plugin path')
        ctx.exit()
    if not directory:
        directory = os.path.join(get_user_idadir(), 'plugins')
        os.makedirs(directory) if not os.path.exists(directory) else None
    store_path = os.path.join(directory, 'ida_binaryai.py')
    click.echo("installing ida_binaryai.py into {}".format(directory))
    plugin_code = """# generated by `binaryai install_ida_plugin`
def PLUGIN_ENTRY():
    from binaryai import ida_binaryai
    return ida_binaryai.BinaryAIIDAPlugin()
"""
    try:
        with open(store_path, "w") as f:
            f.write(plugin_code)
    except Exception:
        click.echo("Error while installing ida_binaryai.py.")
        ctx.exit()
    click.echo("Done")


@cli.command('query_function', short_help='get function info by given id')
@click.option('--funcid', '-f', help='function id', required=True)
@click.option('--cfg', '-c', help='binaryai configuration file', type=click.File(), show_default=True,
              default=os.path.join(get_user_idadir(), "cfg", "{}.cfg".format(binaryai.__name__)))
@click.pass_context
def QueryFunction(ctx, funcid, cfg):
    cfg_dict = json.loads(cfg.read())
    client = Client(cfg_dict['token'], cfg_dict['url'])
    result = query_function(client, funcid)
    result.pop("sourceCode", None)
    result = json.dumps(result, sort_keys=True, indent=2)
    click.echo(result)


@cli.command('create_funcset', short_help='create a new function set')
@click.option('--name', '-n', help='funcset name', type=str, required=True)
@click.option('--cfg', '-c', help='binaryai configuration file', type=click.File(), show_default=True,
              default=os.path.join(get_user_idadir(), "cfg", "{}.cfg".format(binaryai.__name__)))
@click.pass_context
def CreateFuncSet(ctx, cfg, name):
    cfg_dict = json.loads(cfg.read())
    client = Client(cfg_dict['token'], cfg_dict['url'])
    result = create_function_set(client, name)
    click.echo(json.dumps({"funcsetid": result}))


@cli.command('query_funcset', short_help='get function set info by id')
@click.option('--funcset', '-s', help='funcset id', type=str, required=True)
@click.option('--cfg', '-c', help='binaryai configuration file', type=click.File(), show_default=True,
              default=os.path.join(get_user_idadir(), "cfg", "{}.cfg".format(binaryai.__name__)))
@click.pass_context
def QueryFuncSet(ctx, funcset, cfg):
    cfg_dict = json.loads(cfg.read())
    client = Client(cfg_dict['token'], cfg_dict['url'])
    result = json.dumps(query_function_set(client, funcset), sort_keys=True, indent=2)
    click.echo(result)


@cli.command('upload_functions', short_help='upload the functions of the chosen file')
@click.option('--file', '-f', help='file to be uploaded', type=str, required=True)
@click.option('--idat', '-i', help='path of idat/idat64', type=str, required=True)
@click.option('--funcset', '-s', help='function set you want to upload to', type=str, required=False, default='')
@click.pass_context
def UploadFunctions(ctx, file, idat, funcset):
    plugin_path = get_plugin_path()
    log_path = os.path.join(get_user_idadir(), "log.txt")
    cmd_str = '"{}" -L"{}" -A -S"{} 1 {}" {}'.format(idat, log_path, plugin_path, funcset, file)
    try:
        p = subprocess.Popen(cmd_str, shell=True)
        retcode = p.wait()
        if retcode != 0:
            print("Upload functions fail, please check {} for more detials".format(log_path))
            ctx.exit()
    except FileNotFoundError as e:
        print(e)
        ctx.exit()
    click.echo("Done")


@cli.command('match_functions', short_help='match the functions of the chosen file')
@click.option('--file', '-f', help='file to be matched', type=str, required=True)
@click.option('--idat', '-i', help='path of idat/idat64', type=str, required=True)
@click.pass_context
def MatchFunctions(ctx, file, idat):
    plugin_path = get_plugin_path()
    log_path = os.path.join(get_user_idadir(), "log.txt")
    cmd_str = '"{}" -L"{}" -A -S"{} 2" {}'.format(idat, log_path, plugin_path, file)
    try:
        p = subprocess.Popen(cmd_str, shell=True)
        retcode = p.wait()
        if retcode != 0:
            print("Match functions fail, please check {} for more details".format(log_path))
            ctx.exit()
        # print idb store path
        idat_base = os.path.splitext(idat)[0]
        idb_or_i64 = "idb" if idat_base.endswith("idat") else "i64"
        print("idb file is stored in {}.{}".format(os.path.abspath(file), idb_or_i64))
    except FileNotFoundError as e:
        print(e)
        ctx.exit()
    click.echo("Done")


def main():
    cli()
