# -*- coding: utf-8 -*-
"""
@Created On 2019-03-26
@Updated On 2019-03-26
@Author: tx
"""
# pip install requests
# pip install baidu-aip
# pip install fake_useragent

import os
import re
import json
import time
import requests
from aip import AipSpeech
from fake_useragent import UserAgent



def get_ip():
    """
    获取本机IP和地理位置
    """
    res = requests.get("http://www.ip.cn")
    result = re.findall("<p>您现在的 IP：<code>(.*?)</code></p><p>所在地理位置：<code>(.*?)</code>", res.text)
    ip, address = "", ""
    if len(result):
        ip = result[0][0]  # IP地址
        address = result[0][1].split(' ')[0]  # 地理位置
    else:
        print("Not Match IP")

    return ip, address


class MyRequest(object):
    """
    自定义requests请求

    """
    def __init__(self):
        self.headers = dict()
        self.headers['User-Agent'] = UserAgent().random
        self.my_session = requests.session()

    def _update_headers(self, headers=None):
        if headers:
            self.headers.update(headers)

    def _my_request(self, url, headers=None, data=None):
        self._update_headers(headers)
        if not data or len(data) == 0:
            res = self.my_session.get(url, headers=self.headers)
        else:
            res = self.my_session.post(url, headers=self.headers, data=data)
        if str(res.status_code)[0] != '2':
            print("request failed, URL: " + url)
            return ''
        else:
            res.encoding = "utf-8"
            return res.text    


class GetWeather(MyRequest):
    """
    根据城市对应编码获取天气信息
    """
    def __init__(self, city_code):
        super(GetWeather, self).__init__()
        self.city_code = city_code

    def get_weather(self):
        url = "http://d1.weather.com.cn/sk_2d/{}.html?_=1544842784069".format(self.city_code)
        while 1:
            headers = {"Referer": "http://www.weather.com.cn/weather1d/{}.shtml".format(self.city_code)}
            res_text = self._my_request(url, headers=headers)
            if not re.search('FlashVars', res_text):
                break
        js = json.loads(res_text.lstrip('var dataSK = '))
        weather_info = {
            "日期": js['date'],
            "天气": js['weather'],
            "温度": js['temp'] + '℃',
            "PM2.5": js['aqi_pm25'],
            "相对湿度": js['SD'],
        }
        return weather_info


class CityCode(MyRequest):
    """
    获取城市编码数据，并保存到本地json文件
    获取对应城市的编码
    """
    def __init__(self, file='./doc/city_code.json'):
        super(CityCode, self).__init__()
        self.city_file = file
        self.city_dict = self.get_city_map()

    def _check_dir(self, file_dir):
        if not os.path.isdir(file_dir):  
            os.makedirs(file_dir)

    def get_city_map(self):
        try:
            with open(self.city_file , 'r') as fp:
                city_dict = dict()
                city_dict = json.load(fp)
            if city_dict:
                return city_dict
        except Exception as e:
            pass

        url = "http://map.weather.com.cn/static_data/101.js"
        res_text = self._my_request(url)
        if not res_text:
            return {}
        js = json.loads(res_text.lstrip('var map_config_101='))

        province_list = []
        for item in js['text']['inner']:
            province_list.append((item['data-name'], item['data-id']))

        city_dict = dict()
        for pro in province_list:
            time.sleep(1)
            province_name = pro[0]
            province_code = pro[1]
            href = "http://map.weather.com.cn/static_data/{}.js".format(province_code)
            res = self._my_request(href)
            if not res:
                continue
            js = json.loads(res.lstrip('var map_config_{}='.format(province_code)))
            for city in js['text']['inner']:
                if province_name in ['北京', '上海', '天津', '重庆']:
                    city_dict[province_name + "-" + city['data-name']] = city['data-id']
                else:
                    city_dict[province_name+ "-" + city['data-name']] = city['data-id'] + "01"

        self._check_dir(os.path.dirname(self.city_file))
        with open(self.city_file, 'w') as fp:
            json.dump(city_dict, fp)
        return city_dict


    def get_city_id(self, city_name):
        """
        获取城市对应的编码
        """
        city_id = self.city_dict.get(city_name, '')
        return city_id


class BaiduAipSpeech(object):
    """
    使用百度的语音接口将中文文字转换为语音
    """
    def __init__(self):
        self._app_id = 'xxxxxxxx'
        self._api_key = 'xxxxxxxxxxxxxxxxxxxxxxxx'
        self._secret_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' 
        self.file_dir = './mp3'
        self._check_dir(self.file_dir)

    def _check_dir(self, file_dir):
        if not os.path.isdir(file_dir):  
            os.makedirs(file_dir)

    def get_mp3(self, text):
        """
        获取中文文字语音文件
        """
        client = AipSpeech(self._app_id, self._api_key, self._secret_key)
        result = client.synthesis(text, 'zh', 1, {"spd":4, "vol": 6})

        # 识别正确返回语音二进制 错误则返回dict
        if not isinstance(result, dict):
            mp3 = 'weather_{}.mp3'.format(int(time.time()))
            file = os.path.join(self.file_dir, mp3)
            with open(file, 'wb') as fp:
                fp.write(result)
            return file
        else:
            print("Get MP3 Error!")
            return ''


def main():
    ip, address = get_ip()
    if not ip or not address:
        print("Get IP Error!")
        exit()

    try:
        # 简陋的提取地址信息
        pattern = r'(.*?)[省|市|](.*?)[市|区|县]'
        res_text = re.search(pattern, address)
        if not res_text:
            print("Get City Error!")
            exit()

        res = res_text.groups()
        city = res[0] + '-'+ res[1]
    except Exception as e:
        print("Get City Error!")  

    file = './doc/city_code.json'
    cc_obj = CityCode(file)
    city_id = cc_obj.get_city_id(city)
    if not city_id:
        print("Get City Code Error!")
        exit()

    wea = GetWeather(city_id)
    weather_info = wea.get_weather()
    if not weather_info:
        print(ip, city)
        print("Get Weather Info Error!")
        exit()

    words = "{}的天气情况如下：{}".format(address, weather_info)
    speech_obj = BaiduAipSpeech()
    mp3_file = speech_obj.get_mp3(words)

    print("Done!")
    print(ip, city)
    print(weather_info)
    print("mp3 file: ", mp3_file)


if __name__ == '__main__':
    main()
