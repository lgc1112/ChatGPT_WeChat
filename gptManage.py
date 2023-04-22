import time
import requests
import json
import math
import random
import logging
import azure.cognitiveservices.speech as speechsdk
from wechatpy import WeChatClient
from wechatpy.replies import VoiceReply

import threading
import os
from os import listdir

import yaml
with open('config/config.yml', 'r') as f:
    configs = yaml.load(f, Loader=yaml.FullLoader)
from revChatGPT.V1 import Chatbot
chatbot = Chatbot(config={
  "email":  configs['openai']['account'],
  "access_token":  configs['openai']['api_keys']
})
fmt = '[%(asctime)-15s]-[%(process)d:%(levelname)s]-[%(filename)s:%(lineno)d]-%(message)s'
logging.basicConfig(filename = './chat.log', level = logging.DEBUG, format=fmt)
# logging.basicConfig(level=logging.DEBUG, format=fmt)


class gptSessionManage(object):
    '''
    会话管理器，保存发送和接受的消息，构造消息模板，实现上下文理解。
    '''

    def __init__(self, save_history):
        '''
        初始化
        '''
        self.messages = [{"role": "system", "content": configs['openai']['system_prompt']}, ]
        self.sizeLim = save_history
        self.last_q_time = time.time()

    def add_send_message(self, msg):
        '''
        会话管理, 拼接回复模板
        '''
        # # 清理超过10分钟的会话
        # if time.time() - self.last_q_time > 600:
        #     self.end_message()
        # 判断会话长度是否超过限制
        if len(self.messages) > self.sizeLim:
            self.messages.pop(1)
            self.messages.pop(1)
        self.messages.append({"role": "user", "content": f"{msg}"})
        # 记录时间节点
        self.last_q_time = time.time()

    def add_res_message(self, msg):
        '''
        添加openai回复消息内容
        '''
        self.messages.append({"role": "assistant", "content": f"{msg}"})

    def end_message(self, to_voice = False):
        '''
        初始化会话
        '''
        if to_voice:
            self.messages = [{"role": "system", "content": configs['openai']['english_system_prompt']}]
        else:
            self.messages = [{"role": "system", "content": configs['openai']['system_prompt']}]

    def get_message(self):
        self.messages


class userMgr(object):
    '''
    每个用户的管理器，保存发送和接受的消息，构造消息模板，实现上下文理解。
    '''

    def __init__(self, msg_mgr, session_mgr):
        '''
        初始化
        '''
        self.waiting_rsp_msg_id = 0
        self.timeout_waiting_rsp_msg_id = 0
        self.session_mgr = session_mgr
        self.recv_rsp_msg = ''
        self.latest_req_time = 0
        self.req_times = 0
        self.messages = []
        self.msg_mgr = msg_mgr
        self.conversation_id = ''
        self.parent_id = ''
        self.is_english_teacher_mode = False
        self.err_num = 0
        
    def clear(self):
        self.waiting_rsp_msg_id = 0
        self.timeout_waiting_rsp_msg_id = 0
        self.session_mgr.end_message()
        self.recv_rsp_msg = ''
        self.latest_req_time = 0
        self.req_times = 0
        self.messages = []
        self.conversation_id = ''
        self.parent_id = ''
        self.err_num = 0

    def transfer_voice(self):
        self.waiting_rsp_msg_id = 0
        self.timeout_waiting_rsp_msg_id = 0
        self.session_mgr.end_message(True)
        self.recv_rsp_msg = ''
        self.latest_req_time = 0
        self.req_times = 0
        self.messages = []
        self.conversation_id = ''
        self.parent_id = ''
        self.err_num = 0
    
    def set_waiting_rsp_msg_id(self, msg_id):
        self.waiting_rsp_msg_id = msg_id

    def get_waiting_rsp_msg_id(self):
        return self.waiting_rsp_msg_id

    def get_timeout_waiting_rsp_msg_id(self):
        return self.timeout_waiting_rsp_msg_id

    def set_session_mgr(self, session_mgr):
        self.session_mgr = session_mgr

    def get_session_mgr(self):
        return self.session_mgr

    def set_recv_rsp_msg(self, recv_rsp_msg):
        self.recv_rsp_msg = recv_rsp_msg

    def get_recv_rsp_msg(self):
        return self.recv_rsp_msg

    def set_latest_req_time(self, latest_req_time):
        self.latest_req_time = latest_req_time

    def get_latest_req_time(self):
        return self.latest_req_time

    def set_req_times(self, req_times):
        self.req_times = req_times

    def get_req_times(self):
        return self.req_times

    def send_request(self, msgs):
        '''text消息处理'''
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.msg_mgr.get_header(),
            }
            logging.debug('发送的消息：' + str(self.session_mgr.messages))
            btime = int(time.time())

            json_data = {
                'model': self.msg_mgr.model,
                'messages': self.session_mgr.messages,
                'max_tokens': self.msg_mgr.max_tokens,
                'temperature': self.msg_mgr.temperature,
            }


            # answer = ''
            # new_conversation_id = ''
            # new_parent_id = ''
            # logging.info(f'old_conversation_id={self.conversation_id}, new_parent_id={self.parent_id}')
            # prompt = configs['openai']['system_prompt']
            # logging.info(f'query={msgs.content} query={prompt}')
            # if (self.conversation_id == ''):
            #     for data in chatbot.ask(prompt, self.conversation_id, self.parent_id):
            #         self.conversation_id = data['conversation_id']
            #         self.parent_id = data['parent_id']
                 
            # for data in chatbot.ask(f"{msgs.content}", self.conversation_id, self.parent_id):
            #     answer = data['message']
            #     self.conversation_id = data['conversation_id']
            #     self.parent_id = data['parent_id']
            #     model = data['model']
            # logging.info(f'query={msgs.content}, model = {model}, answer={answer}, new_conversation_id={self.conversation_id}, new_parent_id={self.parent_id}')
            # return answer
            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=json_data,
                                     timeout=120)
            response_parse = json.loads(response.text)
            logging.debug('收到的消息：' + str(response_parse))
            atime = int(time.time())
            logging.debug('收到的时间差：%d s,%d,%d' % (atime - btime, btime, atime))
            if 'error' in response_parse:
                logging.debug('咨询人数过多，请稍后再试！')
                return '咨询人数过多，请稍后再试！'
            else:
                self.session_mgr.add_res_message(
                    response_parse['choices'][0]['message']['content'])
                
                return response_parse['choices'][0]['message']['content']
        except Exception as e:
            logging.debug(e)
            logging.debug('请求超时，请稍后再试！')
            # return '请求超时，请稍后再试！\n【近期官方接口响应变慢，若持续出现请求超时，还请换个时间再来😅~】'
            return '请求超时，请稍后再试！'

        
    def send_request_voice(self, msgs):
        '''voice消息处理'''
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.msg_mgr.get_header(),
            }
            logging.debug('发送的消息：' + str(self.session_mgr.messages))

            json_data = {
                'model': self.msg_mgr.model,
                'messages': self.session_mgr.messages,
                'max_tokens': self.msg_mgr.configs['azure']['max_token'],
                'temperature': self.msg_mgr.temperature,
            }

            btime = int(time.time())
            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=json_data,
                                     timeout=120)
            response_parse = json.loads(response.text)
            logging.debug('收到的消息：' + str(response_parse))
            atime = int(time.time())
            logging.debug('收到的时间差：%d s,%d,%d' % (atime - btime, btime, atime))
            
            if 'error' in response_parse:
                logging.debug('咨询人数过多，请稍后再试！')
                return '咨询人数过多，请稍后再试！'
            else:
                rtext = response_parse['choices'][0]['message']['content']
                logging.debug('开始转语音:' + str(rtext))
                if self.msg_mgr.get_voice_from_azure(rtext, str(msgs.source), str(msgs.id)):
                    logging.debug('转语音成功:' + str(rtext))
                    media_id = self.msg_mgr.upload_wechat_voice(str(msgs.source), str(msgs.id))
                    logging.debug('media_id:' + str(media_id))
                    if media_id:
                        reply = VoiceReply(message=msgs)
                        reply.media_id = str(media_id)
                        time.sleep(1.2)
                        self.session_mgr.add_res_message(rtext)
                        return [reply]
                    else:
                        return rtext
                else:
                    logging.debug('转语音失败:' + str(rtext))
                    self.session_mgr.add_res_message(rtext)
                    return rtext
        except Exception as e:
            logging.debug(e)
            logging.debug('请求超时，请稍后再试！')
            return '请求超时，请稍后再试！'

    def runable_task(self):
        msg_id = self.waiting_rsp_msg_id
        logging.debug('start thread... id:' + str(msg_id))
        time.sleep(14)
        if (msg_id == self.waiting_rsp_msg_id):
            self.timeout_waiting_rsp_msg_id = msg_id
            logging.debug('thread timeout... id:' + str(msg_id))
        else:
            logging.debug('waiting_rsp_msg_id发生修改，对话已不需要记录，msg_id：{}，waiting_rsp_msg_id：{}'.format(self.timeout_waiting_rsp_msg_id, msg_id))
            

    def get_responce_first(self, msg):
        '''
        首次消息开始处理
        '''

        self.waiting_rsp_msg_id = msg.id
        logging.debug('get_responce_first:' + str(msg.id) + str(msg))
        t = threading.Thread(target=self.runable_task)
        t.start()
        if msg.type == 'text' or self.msg_mgr.configs['azure']['trans_to_voice'] == False:
            self.session_mgr.add_send_message(msg.content)
            res = self.send_request(msg)
        else:
            self.session_mgr.add_send_message(msg.recognition)
            res = self.send_request_voice(msg)
            
        if self.waiting_rsp_msg_id == msg.id:
            self.set_recv_rsp_msg(res)
        else:
            logging.debug('对话已经发生重入, waiting_rsp_msg_id:{}, msg.id:{}', self.waiting_rsp_msg_id, msg.id)
        return 'success'

    def get_responce_not_first(self, msg):
        '''
        pending状态的消息等候
        '''
        while self.get_recv_rsp_msg() == '':
            time.sleep(0.1)
        return 'success'


lock = threading.Lock()
class gptMessageManage(object):
    '''
    消息管理器，接受用户消息，回复用户消息
    '''

    def __init__(self, wechat_client, configs):
        self.client = wechat_client
        self.configs = configs
        # 基础设置
        self.tokens = configs['openai']['api_keys']
        self.model = configs['openai']['model']
        self.temperature = configs['openai']['temperature']
        self.max_tokens = configs['openai']['max_tokens']  # 每条消息最大字符
        self.rsize = configs['openai']['rsize']  # 设置每条消息的回复长度，超过长度将被分割
        # 记录信息的列表和字典
        self.msgs_list = dict()  # msgID作为key，三次重复发送的msg放置在一个列表，结合append和pop构造队列，以实现轮流处理重复请求
        self.msgs_time_dict = dict()  # 记录每个msgID最新的请求时间
        self.msgs_status_dict = dict()  # 记录每个msgID的状态：pending,haveResponse
        self.msgs_returns_dict = dict()  # 记录每个msgID的返回值
        self.msgs_msgdata_dict = dict()  # 记录每个发送者的会话管理器gptSessionManage
        self.user_mgrs = dict()  # 记录每个发送者的会话管理器gptSessionManage
        self.msgs_msg_cut_dict = dict()  # 记录每个msgID超过回复长度限制的分割列表

        self.user_msg_timeSpan_dict = dict()  # 记录每个发送消息者的时间消息时间间隔
        self.user_msg_timePoint_dict = dict()  # 记录每个发送消息者的上次时间点

        self.media_id_list = []  # 用于记录上传到微信素材的media_id

        self.last_clean_time = time.time()

    def get_response(self, msgs, curtime, msg_content):
        '''
        获取每条msg，回复消息
        '''
        logging.debug('get_request:' + str(msgs.id) + str(msg_content))
        # self.msgs_time_dict[str(msgs.id)] = curtime
        user_mgr = self.user_mgrs.get(str(msgs.source), None)
        if user_mgr is None:
            user_mgr = userMgr(self, gptSessionManage(self.configs['openai']['save_history']))
            self.user_mgrs[str(msgs.source)] =user_mgr

        if msgs.type == 'text' and user_mgr.is_english_teacher_mode and self.have_chinese(msg_content):
            logging.debug('Transfer Chinese:' + str(msgs.id) + str(msg_content))
            user_mgr.is_english_teacher_mode = False
            user_mgr.clear()
            
        # 切换英语口语模式
        if msgs.type == 'voice' and not user_mgr.is_english_teacher_mode and not self.have_chinese(msg_content):
            logging.debug('Transfer English:' + str(msgs.id) + str(msg_content))
            user_mgr.is_english_teacher_mode = True
            user_mgr.transfer_voice()
            

        oldTime = user_mgr.get_latest_req_time()
        user_mgr.set_latest_req_time(curtime)
        # req_times = user_mgr.get_req_times() + 1
        # user_mgr.set_req_times(req_times)

        # 判断是否返回分割列表里面的内容
        if msg_content == '1':
            if len(self.msgs_msg_cut_dict.get(str(msgs.source), [])) > 0:
                if len(self.msgs_msg_cut_dict[str(msgs.source)]) > 1:
                    return self.msgs_msg_cut_dict[str(msgs.source)].pop(0) + '\n 还有剩余结果，请回复【1】查看！'
                else:
                    return self.msgs_msg_cut_dict[str(msgs.source)].pop(0)
            else:
                if user_mgr.get_waiting_rsp_msg_id() == 0 and user_mgr.get_recv_rsp_msg() == '':
                    return '没有消息啦'
                if user_mgr.get_recv_rsp_msg() == '' and \
                user_mgr.get_timeout_waiting_rsp_msg_id() == user_mgr.get_waiting_rsp_msg_id():
                    user_mgr.timeout_waiting_rsp_msg_id = 0
                    t = threading.Thread(target=user_mgr.runable_task)
                    t.start()
                res = 'success'
        elif msg_content == '$new':
            user_mgr.clear()
            logging.debug("$new1")
            return '对话历史已经清空'
        else:
            waiting_rsp_user_id = user_mgr.get_waiting_rsp_msg_id()
            # 收到新消息
            if waiting_rsp_user_id == 0:
                res = user_mgr.get_responce_first(msgs)
            else:
                if waiting_rsp_user_id != msgs.id:
                    user_mgr.err_num += 1
                    if user_mgr.err_num == 3:
                        logging.debug("请等待上一句咨询回复完成后再发新的对话, num:{}".format(user_mgr.err_num))
                    else:
                        logging.debug("$clear")
                        user_mgr.clear()
                        return '对话历史已经清空'

                    user_mgr.set_latest_req_time(oldTime)
                    user_mgr.err_num += 1
                    return '请等待上一句话咨询回复完成后再开始下一句咨询'

        logging.debug('1111记录时间：{}, 当前时间:{}, waiting_rsp_msg_id:{}, timeout_id:{}, recv_msg:{}'.format(
            user_mgr.get_latest_req_time(), curtime, user_mgr.get_waiting_rsp_msg_id(),
            user_mgr.get_timeout_waiting_rsp_msg_id(), user_mgr.get_recv_rsp_msg()))
        
        while user_mgr.get_recv_rsp_msg() == '' and \
                user_mgr.get_timeout_waiting_rsp_msg_id() != user_mgr.get_waiting_rsp_msg_id():
            time.sleep(0.1)

        if (user_mgr.get_timeout_waiting_rsp_msg_id() == user_mgr.get_waiting_rsp_msg_id()
                and user_mgr.get_recv_rsp_msg() != ''):
                logging.debug('读取消息超时')

        # lock.acquire()
        # recvmsg = user_mgr.get_recv_rsp_msg()
        # user_mgr.set_recv_rsp_msg('')
        # logging.debug('收到结果', str(recvmsg))
        # lock.release()

        logging.debug('2222记录时间：{}, 当前时间:{}, waiting_rsp_msg_id:{}, timeout_id:{}, recv_msg:{}'.format(
            user_mgr.get_latest_req_time(), curtime, user_mgr.get_waiting_rsp_msg_id(),
            user_mgr.get_timeout_waiting_rsp_msg_id(), user_mgr.get_recv_rsp_msg()))

        # 判断当前请求是否是最新的请求，是：返回消息，否：返回空
        if curtime == user_mgr.get_latest_req_time():
            if (user_mgr.get_timeout_waiting_rsp_msg_id() == user_mgr.get_waiting_rsp_msg_id()
                    and user_mgr.get_recv_rsp_msg() == ''):
                logging.debug('人数过多，咨询超时，请回复【1】继续上一条咨询')
                return '人数过多，咨询超时，请回复【1】继续上一条咨询'
            recvmsg = user_mgr.get_recv_rsp_msg()
            user_mgr.set_recv_rsp_msg('')
            user_mgr.set_waiting_rsp_msg_id(0)
            logging.debug('回复-------' + str(recvmsg))
            retunsMsg = recvmsg
            # 清理缓存
            t = threading.Thread(target=self.del_cache)
            t.start()
            # 是否返回的语音消息的media_id
            if isinstance(retunsMsg, list):
                logging.debug('返回语音的列表：' + str(recvmsg))
                return retunsMsg
            # 判断长度是否过长，否则将消息分割
            if len(retunsMsg) > self.rsize:
                ssss = math.ceil(len(retunsMsg) / self.rsize)
                cutmsgs = []
                for i in range(ssss):
                    if i == ssss - 1:
                        cutmsgs.append(retunsMsg[i * self.rsize:])
                    else:
                        cutmsgs.append(retunsMsg[i * self.rsize:i * self.rsize + self.rsize])
                self.msgs_msg_cut_dict[str(msgs.source)] = cutmsgs
                return self.msgs_msg_cut_dict[str(msgs.source)].pop(0) + '\n 还有剩余结果，请回复【1】查看！'
            return retunsMsg
        else:
            logging.debug('该旧请求不需要回复:time:{}, 内容：{}'.format(curtime, msg_content))
            # self.del_cache()
            time.sleep(4)
            return ''

    def rec_get_returns_pending(self, msgs, user_mgr):
        '''
        pending状态的消息等候
        '''
        if user_mgr.get_waiting_rsp_msg_id() != 0:
            time.sleep(0.1)
        return 'success'

        # while self.msgs_status_dict.get(str(msgs.id), '') == 'pending':
        #     time.sleep(0.1)
        # return 'success'

    def rec_get_returns_first(self, msgs):
        '''
        首次消息开始处理
        '''
        while len(self.msgs_list[str(msgs.id)]) > 0:
            mymsg = self.msgs_list[str(msgs.id)].pop(0)
            if msgs.type == 'text' or self.configs['azure']['trans_to_voice'] == False:
                self.msgs_returns_dict[str(mymsg.id)] = self.send_request(mymsg)
            else:
                self.msgs_returns_dict[str(mymsg.id)] = self.send_request_voice(mymsg)
        self.msgs_status_dict[str(mymsg.id)] = 'haveResponse'
        return 'success'

    def get_header(self):
        '''
        随机获取token，可以设置多个token，避免单个token超过请求限制。
        '''
        return random.choice(self.tokens)

    def send_request(self, msgs):
        '''text消息处理'''
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.get_header(),
            }
            logging.debug('发送的消息：' + str(self.msgs_msgdata_dict[str(msgs.source)].messages))
            btime = int(time.time())

            json_data = {
                'model': self.model,
                'messages': self.msgs_msgdata_dict[str(msgs.source)].messages,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
            }

            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=json_data,
                                     timeout=30)
            response_parse = json.loads(response.text)
            logging.debug('收到的消息：' + str(response_parse))
            atime = int(time.time())
            logging.debug('收到的时间差：%d s,%d,%d' % (atime - btime, btime, atime))
            if 'error' in response_parse:
                print(response_parse)
                return '出错了，请稍后再试！'
            else:
                self.msgs_msgdata_dict[str(msgs.source)].add_res_message(
                    response_parse['choices'][0]['message']['content'])
                return response_parse['choices'][0]['message']['content']
        except Exception as e:
            print(e)
            # return '请求超时，请稍后再试！\n【近期官方接口响应变慢，若持续出现请求超时，还请换个时间再来😅~】'
            return '请求超时，请稍后再试！'

    def send_request_voice(self, msgs):
        '''voice消息处理'''
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.get_header(),
            }
            print('发送的消息：', self.msgs_msgdata_dict[str(msgs.source)].messages)

            json_data = {
                'model': self.model,
                'messages': self.msgs_msgdata_dict[str(msgs.source)].messages,
                'max_tokens': self.configs['azure']['max_token'],
                'temperature': self.temperature,
            }

            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=json_data,
                                     timeout=9)
            response_parse = json.loads(response.text)
            logging.debug(response_parse)
            if 'error' in response_parse:
                logging.debug(response_parse)
                return '出错了，请稍后再试！'
            else:
                rtext = response_parse['choices'][0]['message']['content']
                if self.get_voice_from_azure(rtext, str(msgs.source), str(msgs.id)):
                    media_id = self.upload_wechat_voice(str(msgs.source), str(msgs.id))
                    logging.debug('media_id:' + str(media_id))
                    if media_id:
                        self.msgs_msgdata_dict[str(msgs.source)].add_res_message(rtext)
                        return [str(media_id)]
                    else:
                        return rtext
                else:
                    self.msgs_msgdata_dict[str(msgs.source)].add_res_message(rtext)
                    return rtext
        except Exception as e:
            logging.debug(e)
            return '请求超时，请稍后再试！'

    def get_voice_from_azure(self, texts, msgsource, msgid):
        '''
        从AZURE获取文本转语音的结果
        '''
        logging.debug('从AZURE获取文本转语音的结果')
        try:
            speech_config = speechsdk.SpeechConfig(subscription=self.configs['azure']['acess_token'], region=self.configs['azure']['region'])
            # speech_config = speechsdk.SpeechConfig(auth_token=self.configs['azure']['auth_token'])
            speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
            if self.have_chinese(texts):
                # speech_config.speech_synthesis_voice_name ="zh-CN-YunxiNeural"
                speech_config.speech_synthesis_voice_name =self.configs['azure']['zh_model']
            else:
                # speech_config.speech_synthesis_voice_name ="en-US-GuyNeural"
                speech_config.speech_synthesis_voice_name =self.configs['azure']['en_model']
            audio_config = speechsdk.audio.AudioOutputConfig(filename=f"voice/{msgsource[-5:]+msgid[-5:]}.mp3")
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            speech_synthesis_result = speech_synthesizer.speak_text_async(f"{texts}").get()
            # rr = speech_synthesizer.speak_text(f"{texts}")
            logging.debug('dddddd:'+ str(f"{texts}") + 'reason:' + str(speech_synthesis_result.__str__()))
            if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            else:
                cancellation_details = speech_synthesis_result.cancellation_details
                print("Speech synthesis canceled: {}".format(cancellation_details.reason))
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    if cancellation_details.error_details:
                        print("Error details: {}".format(cancellation_details.error_details))
                        print("Did you set the speech resource key and region values?")
                return False
        except Exception as e:
            
            logging.debug('从AZURE获取文本转语音的结果错误:{}'.format(str(e)))
            return False

    def upload_wechat_voice(self, msgsource, msgid):
        '''上传语音素材到微信'''
        try:
            with open(f"voice/{msgsource[-5:] + msgid[-5:]}.mp3", "rb") as f:
                res = self.client.material.add('voice', f)
                media_id = res['media_id']
                self.media_id_list.append(media_id)
            return media_id
        except Exception as e:
            print(e)
            return

    def have_chinese(self, strs):
        '''判断是否有中文'''
        for _char in strs[:8]:
            if '\u4e00' <= _char <= '\u9fa5':
                return True
        return False

    def del_uploaded_wechat_voice(self, mediaId):
        '''删除上传的语音素材'''
        try:
            self.client.material.delete(mediaId)
            return 1
        except Exception as e:
            print(e)
            return 1

    def del_cache(self):
        '''
        清除缓存
        '''
        time.sleep(5)
        if time.time() - self.last_clean_time > 300:
            currenttt = int(time.time())
            delkey_lis = []
            for key, value in self.msgs_time_dict.items():
                if currenttt - value > 30:
                    delkey_lis.append(key)
            for key in delkey_lis:
                self.msgs_time_dict.pop(key, '')
                self.msgs_status_dict.pop(key, '')
                self.msgs_returns_dict.pop(key, '')
                self.msgs_list.pop(key, '')
            self.last_clean_time = time.time()
            my_path = 'voice/'

            for file_name in listdir(my_path):
                try:
                    os.remove(my_path + file_name)
                except Exception:
                    print('删除失败')
            # 删除media_id：
            for mid in self.media_id_list:
                self.del_uploaded_wechat_voice(mid)
            self.media_id_list = []
        return
