# 导入模块
import hashlib
from flask import Flask, request, make_response
from flask import abort
from wechatpy import parse_message, create_reply, WeChatClient
from wechatpy.replies import VoiceReply
import wechatpy
import time
import os
import yaml
from whiteIPManage import whiteIP
from gptManage import gptSessionManage,gptMessageManage

##############################读取配置##########################
with open('config/config.yml', 'r') as f:
    configs = yaml.load(f, Loader=yaml.FullLoader)
##############################设置微信相关参数##########################
appid = configs['wechat']['appid']
secret = configs['wechat']['secret']
if configs['wechat']['ip_detection'] or configs['azure']['trans_to_voice']:
    client = WeChatClient(appid, secret)
else: 
    client = ''
wechattoken = configs['wechat']['token']

##############################设置IP白名单,预防doss##########################
mywhiteIP = whiteIP(client)

##############################openai基础设置##########################
msgsmanag = gptMessageManage(client,configs)


app = Flask(__name__)
app.debug = True


import logging
fmt = '[%(asctime)-15s]-[%(process)d:%(levelname)s]-[%(filename)s:%(lineno)d]-%(message)s'
logging.basicConfig(filename = './chat.log', level = logging.DEBUG, format=fmt)
# logging.basicConfig(level = logging.DEBUG, format=fmt)
# 导入自定义类

# @app.route("/")
# def hello():
#     return "Hello test!"

@app.route('/callback', methods=['GET', 'POST']) 
def wechat():
    global reply
    global msgsmanag
    global wechattoken
    global mywhiteIP
    if configs['wechat']['ip_detection']:
        if not mywhiteIP.is_white_ip(request.remote_addr):
            abort(404)
    if request.method == 'GET':
        token = wechattoken# 设置 wechat token
        data = request.args
        signature = data.get('signature', '')
        timestamp = data.get('timestamp', '')
        nonce = data.get('nonce', '')
        echostr = data.get('echostr', '')
        s = sorted([timestamp, nonce, token])
        s = ''.join(s)
        if hashlib.sha1(s.encode('utf-8')).hexdigest() == signature:
            response = make_response(echostr)
            return response
    else:
        msg = parse_message(request.get_data())
        if msg.type == 'text':
            cctime = int(time.time())
            # 内置英语对话模板
            if msg.content[:4]=='英语对话':
                tt = f'''Now please be my English teacher. We will simulate an English chat, and in addition to answering, you also need to point out my expression errors. Today's topic is "{msg.content[4:]}". Your chat response needs to guide me to complete the English topic. If you understand, please reply with the requirements for today's chat practice.'''
                msg.content = tt
                rtext = msgsmanag.get_response(msg,cctime,tt)
            else:
                rtext = msgsmanag.get_response(msg,cctime, msg.content)
            logging.debug('get_rtext:::' + str(rtext))
            if isinstance(rtext, list):
                print('返回的是语音：',rtext)
                reply = rtext[0]
            else:
                rt = str(rtext).strip()
                reply = create_reply(rt, message=msg)
            return reply.render()
        if msg.type == 'voice':
            cctime = int(time.time())
            try:
                logging.debug("收到音频:" + str(msg.recognition))
                rtext = msgsmanag.get_response(msg, cctime, msg.recognition)
            except Exception as e:
                raise
            
            print('打印返回的内容',rtext)
            if isinstance(rtext, list):
                print('返回的是语音：',rtext)
                reply = rtext[0]
            else:
                reply = create_reply(rtext, message=msg)
            return reply.render()
        
        if msg.type == 'image':
            rtext = '抱歉，暂不支持发送图片信息'
            reply = create_reply(rtext, message=msg)#创建消息
            return reply.render()#回复消息
        return ''


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
