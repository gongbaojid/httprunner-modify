import base64
import json
import os
import sys
import urllib.parse as urlparse
from loguru import logger
from httprunner.ext.har2all import utils
import requests
import yaml
import os
import shutil
import json
from dotenv import load_dotenv
import time
import csv
import string

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


IGNORE_REQUEST_HEADERS = [
    "host",
    "accept",
    "content-length",
    "connection",
    "accept-encoding",
    "accept-language",
    "origin",
    "cache-control",
    "pragma",
    "upgrade-insecure-requests",
    ":authority",
    ":method",
    ":scheme",
    ":path"
]


class HarParser(object):

    def __init__(self, har_file_path, pre_len=0):
        self.har_file_path = har_file_path
        self.pre_len = pre_len

    def is_num(self, x):
        try:
            x = int(x)
            return isinstance(x, int)
        except ValueError:
            return False

    def genarate_api_variables(self, api_path):
        """
        1.加载api文件，解析request中的key为params或者json的字典
        2.将上述字典提取出来，作为variables保存
        3.替换request中的params以及json中的字典value值替换为变量名
        :param api_path: yaml格式的api文件
        :return:
        """
        # 读取api文件并生成字典
        with open(api_path, 'r', encoding='utf-8') as f:
            y = yaml.safe_load(f)
        # 初始化variables字典的值
        y['variables'] = {}
        if 'params' in y['request'].keys():
            y['variables'].update(y['request']['params'])
            for key in y['request']['params'].keys():
                y['request']['params'][key] = '$' + key
        if 'json' in y['request'].keys():
            y['variables'].update(y['request']['json'])
            for key in y['request']['json'].keys():
                y['request']['json'][key] = '$' + key
        with open(api_path, 'w', encoding='utf-8') as f1:
            yaml.dump(y, f1, allow_unicode=True, default_flow_style=False, indent=4)

    def har2yaml(self, path):
        """
        自动生成原始yaml文件
        :param path: yaml文件的路径
        :return: 生成的yaml文件的路径
        """
        command_line = 'har2case {} -2y'.format(path)
        os.system(command_line)
        yaml_path = os.path.splitext(path)[0] + '.yml'
        with open(yaml_path, encoding='utf-8') as f:
            api_list = []
            test_list = []
            x = yaml.safe_load(f)
            while x['teststeps']:
                test = x['teststeps'].pop()
                if test['name'] not in api_list:
                    # 解析request参数中的token字段，并将对应字段替换值
                    if 'token' in test['request']['headers']:
                        test['request']['headers']['token'] = '${get_token()}'
                    # 将已生成的测试步骤保存到api_list中
                    api_list.append(test['name'])
                    test_list.append(test)
            test_list.reverse()
            # config配置项中新增base_url信息
            x["config"]['base_url'] = '${ENV(BaseURL)}'
            x_new = {"config": x["config"], "teststeps": test_list}
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(x_new, f, allow_unicode=True, default_flow_style=False, indent=4)
        return yaml_path

    def genarate_testcase_standard(self, har_file_path, pre_len=0, exluded=None):
        """
        将har直接转换得到的yaml文件自动解析并生成标准的格式化的testcase文件
        :param har_file_path: har文件的地址
        :param exluded: url中需要被排除的后缀
        :return: 测试用例的地址
        """
        # 判断并生成testcases文件夹
        testcase_dir = os.path.join(os.getcwd(), 'testcases')
        # testcase_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0], 'testcases')
        if not os.path.exists(testcase_dir):
            os.mkdir(testcase_dir)

        # 打开转换后的yaml文件，读取teststeps内容
        with open(har_file_path, encoding='utf-8') as f:
            api_list = []
            test_list = []
            x = yaml.safe_load(f)

        # 遍历testcase yaml文件，并对文件内容做解析
        # 替换api内容为api定义的路径
        # 替换request中的token字段为变量名称
        if exluded is None:
            exluded = ['true', 'false']
        while x['teststeps']:
            test = x['teststeps'].pop()
            if test['name'] not in api_list:
                # 解析api的名称，并替换接口测试用例中的request为api的路径
                name_split_list = test['name'][1:].split('/')
                if self.is_num(name_split_list[-1]) or (name_split_list[-1] in exluded):
                    name_split_list.pop()
                api_abspath = 'api/' + '/'.join(name_split_list[pre_len:]) + '.yml'
                # 解析request参数中的token字段，并将对应字段值进行替换
                if 'token' in test['request']['headers']:
                    test['request']['headers']['token'] = '${get_token()}'
                # 将已生成的测试步骤保存到api_list中
                api_list.append(test['name'])
                del test['request']
                del test['validate']
                test['api'] = api_abspath
                test_list.append(test)
        test_list.reverse()

        # config配置项中新增base_url信息
        x["config"]['base_url'] = '${ENV(BaseURL)}'
        x_new = {"config": x["config"], "teststeps": test_list}
        logger.info("begin to write data to new file...")
        testcase_name = os.path.split(har_file_path)[1]
        testcase_path = os.path.join(testcase_dir, testcase_name)
        with open(testcase_path, 'w', encoding='utf-8') as f:
            yaml.dump(x_new, f, allow_unicode=True, default_flow_style=False, indent=4)
        logger.info("write data to new file successed")
        return testcase_path

    def genarate_api(self, path, pre_lenth=0, exluded=None, gen_data=False, ft='yml'):
        """
        自动生成标准化的api文件
        :param path: yaml文件的路径
        :param pre_lenth: uri前几位是无效的，默认3位
        :param gen_data: 是否生成数据文件，默认不生成
        :param ft: 默认生成的文件格式
        :param exluded: api末尾需要被排除的格式
        :return:
        """
        # 获取脚本的路径
        if exluded is None:
            exluded = ['true', 'false']
        script_dir = os.getcwd()
        # script_dir = os.path.split(os.path.realpath(__file__))[0]
        # 判断api文件夹以及data文件夹是否存在
        api_dir = os.path.join(script_dir, 'api')
        data_dir = os.path.join(script_dir, 'data')
        if not os.path.exists(os.path.join(script_dir, 'api')):
            os.mkdir(api_dir)
        if not os.path.exists(os.path.join(script_dir, 'data')):
            os.mkdir(data_dir)

        # 读取yaml测试用例文件内容
        with open(path, encoding='UTF-8') as f:
            x = yaml.safe_load(f)

        # 遍历teststeps生成对应的子目录
        for i in x['teststeps']:
            api_dict = {'teststeps': []}

            # 解析api name，根据api name生成正确的api模块文件夹以及data模块文件夹
            name = i['name']
            uri_list = name[1:].split('/')
            # 若name的最后一个是整型数，则去掉最后一个，判定接口名称为倒数第二个
            if self.is_num(uri_list[-1]) or (uri_list[-1] in exluded):
                uri_list.pop()
            if len(uri_list) >= pre_lenth + 1:
                api_dir_loop = api_dir
                data_dir_loop = data_dir
                for direct in uri_list[pre_lenth:-1]:
                    api_dir_loop = os.path.join(api_dir_loop, direct)
                    data_dir_loop = os.path.join(data_dir_loop, direct)
                    # 判断api的子目录模块名称是否存在
                    if not os.path.exists(api_dir_loop):
                        os.mkdir(api_dir_loop)
                    # 判断data模块名称是否存在
                    if not os.path.exists(data_dir_loop):
                        os.mkdir(data_dir_loop)

                # 判断接口是否存在，不存在生成json文件/yaml以及data中的csv文件
                if ft == 'json':
                    file_path = os.path.join(api_dir_loop, uri_list[-1] + '.json')
                    if not os.path.exists(file_path):
                        with open(file_path, 'a', encoding='utf-8') as api_file:
                            api_dict['config'] = x['config']
                            api_dict['teststeps'].append(i)
                            json_str = json.dumps(api_dict, ensure_ascii=False, indent=4)
                            if isinstance(json_str, bytes):
                                json_str = json_str.decode("utf-8")
                            api_file.write(json_str)
                        # 将生成的api文件的路径写入到描述文件中
                        api_yml_describe_file = os.path.join(os.path.join(script_dir, 'api'), 'api_list.txt')
                        with open(api_yml_describe_file, 'a', encoding='utf-8') as api_describe:
                            api_describe.writelines(file_path + '\n')
                        # if uri_list[3] == 'updateBySjyId':
                        #     print(api_dict)
                else:
                    file_path = os.path.join(api_dir_loop, uri_list[-1] + '.yml')
                    data_file_path = os.path.join(data_dir_loop, uri_list[-1] + '.csv')
                    if not os.path.exists(file_path):
                        with open(file_path, 'a', encoding='utf-8') as api_file:
                            # 后期可以根据需要，将base_url的取值变更为一个变量值
                            i['base_url'] = x['config']['base_url']
                            i['request']['url'] = name
                            yaml.dump(i, api_file, allow_unicode=True, default_flow_style=False, indent=4)
                        # 将生成的api文件的路径写入到描述文件中
                        api_yml_describe_file = os.path.join(os.path.join(script_dir, 'api'), 'api_list.txt')
                        with open(api_yml_describe_file, 'a', encoding='utf-8') as api_describe:
                            api_describe.writelines(file_path + '\n')
                        #  将生成的文件进行变量提取
                        self.genarate_api_variables(file_path)
                    # 根据传参判定是否生成data file
                    if not os.path.exists(data_file_path) and gen_data:
                        # genarate_api_data_file(data_file_path)
                        pass
        return x

    def gen_all(self):
        yaml_path_orignal = self.har2yaml(self.har_file_path)
        self.genarate_api(yaml_path_orignal, self.pre_len)
        self.genarate_testcase_standard(yaml_path_orignal, self.pre_len)
