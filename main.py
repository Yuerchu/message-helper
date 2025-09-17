'''
Author: 于小丘 海枫
Date: 2024-12-23 01:26:26
LastEditors: Yuerchu admin@yuxiaoqiu.cn
LastEditTime: 2024-12-23 02:07:38
FilePath: /巨信文字传输助手/main.py
Description: 

Copyright (c) 2018-2024 by 于小丘Yuerchu, All Rights Reserved. 
'''
import asyncio, aiohttp
from typing import Literal
from nicegui import ui
import datetime
from openai import OpenAI


@ui.page('/')
async def main_page():
    model_list = []

    class message:
        def __init__(self,
                    base_url: str = 'https://127.0.0.1:1234/v1',
                    api_key: str = None):
            self.message = []
            self.base_url = base_url
            self.api_key = api_key
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key if self.api_key is not None else '',
            )
        
        def add(self, text: str, stamp: str = None, role: Literal['system', 'user', 'assistant'] = 'user') -> None:
            """
            向消息列表中添加消息，并在聊天框中显示。
            
            :param text: 消息内容
            :type text: str
            :param stamp: 时间戳，默认为当前时间
            :type stamp: str, optional
            :param role: 消息角色，必须为 'system'、'user' 或 'assistant' 之一，默认为 'user'
            :type role: str, optional
            :raises ValueError: 如果角色不在允许的值中或消息内容为空，则引发 ValueError
            
            :return: None
            """
            
            # 如果消息列表为空且添加的不是系统消息，则先添加系统消息
            if not self.message and role != 'system':
                self.message.append(
                    { "role": 'system', "content": system_prompt.value if system_prompt.value != "" else '你是一个AI助手' }
                )
            
            if role not in ['system', 'user', 'assistant']:
                raise ValueError('The role must be one of "system", "user", or "assistant".') 
            elif text == '':
                raise ValueError('The message content cannot be empty.')
            else:
                self.message.append(
                    { "role": role, "content": text }
                )
            
            # 向消息列表中推送消息
            if role == 'user':
                self.send_message(
                    text=text,
                    name='User',
                    sent=True,
                    stamp=stamp,
                    clean_message=True
                )
            elif role == 'assistant':
                self.send_message(
                    text=text,
                    name='Assistant',
                    sent=False,
                    stamp=stamp
                )
            
            # 滚动到最底部
            chat.scroll_to(percent=1, duration=0.25)
            
        def get_url(self) -> str:
            """获取当前的 API 端点 URL"""
            return self.base_url
        
        def get_key(self) -> str:
            """获取当前的 API Key"""
            return self.api_key
        
        def set_url(self, url: str) -> None:
            """设置 API 端点 URL"""
            self.base_url = url
            self.client.base_url = url
        
        def set_key(self, key: str) -> None:
            """设置 API Key"""
            self.api_key = key
            self.client.api_key = key
        
        # 获取模型列表
        async def get_model(self):
            refreshButton.set_enabled(False)
            notify = ui.notification('正在获取模型列表...', timeout=None)
            notify.spinner = True
            try:
                self.base_url = apiPoint.value
                self.api_key = model_api_key.value
                async with aiohttp.ClientSession() as session:
                    result = await session.get(
                        url=f'{self.base_url}/models',
                        headers={ 'Authorization': f'Bearer {self.api_key}' }
                    )
                models = await result.json()
                print(f'after json: {models}')
                model_list = ['不使用任何模型']
                if 'models' in models:
                    for model in models['models']:
                        # Only add LLM models
                        if model.get('type') == 'llm':
                            if 'loaded_instances' in model and model['loaded_instances']:
                                # For LLM models with loaded instances
                                for instance in model['loaded_instances']:
                                    model_list.append(instance['id'])
                            else:
                                # For LLM models without loaded instances
                                model_list.append(model['key'])
                elif 'data' in models:
                    # Handle the old format for backward compatibility
                    for model in models['data']:
                        model_list.append(model['id'])
            except Exception as e:
                notify.type = 'negative'
                notify.message = f'获取模型列表失败: {str(e)}'
                notify.spinner = False
                await asyncio.sleep(3)
                notify.dismiss()
            else:
                notify.dismiss()
                refreshButton.set_icon('check')
                await asyncio.sleep(1)
                refreshButton.set_icon('refresh')
                return model_list
            finally:
                refreshButton.set_enabled(True)

        # 生成回复
        async def generate_response(self):
            sendButton.set_enabled(False)
            thinking.set_visibility(True)
            message_input.set_enabled(False)
            try:
                completion = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=using_model.value,
                    messages=self.message,
                    n=5,
                    temperature=0.6,
                )
                print(f'Completion: {completion}')
                result = completion.choices[0].message.content
                if enable_tts.value:
                    if tts_type.value == 'CosyVoice':
                        tts_url = f"http://localhost:8000/tts?text={result}"
                        tts_speaker.set_source(tts_url)
                    elif tts_type.value == 'GPT':
                        pass
                self.add(role='assistant', text=result, 
                        stamp=f"{datetime.datetime.now().strftime('%H:%M')} "
                            f"输入提示词: {completion.usage.prompt_tokens} "
                            f"输出提示词: {completion.usage.completion_tokens} "
                            f"总计: {completion.usage.total_tokens}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                ui.notify(f"Error generating response: {str(e)}", color="negative")
            finally:
                sendButton.set_enabled(True)
                message_input.set_enabled(True)
                thinking.set_visibility(False)

        # 发送消息
        def send_message(
            self,
            text: str = '',
            name: str = 'User',
            stamp: str = None,
            sent: bool = True,
            clean_message: bool = False
        ):
            """
            向聊天框发送消息。
            
            :param text: 消息内容
            :type text: str
            :param name: 发送者名称
            :type name: str
            :param sent: 用户发送传入 `True` ，助手发送传入 `False`
            :type sent: bool
            :param clean_message: 是否清空输入框
            :type clean_message: bool
            """
            ui.chat_message(
                text=text, 
                name=name,
                sent=sent,
                stamp=stamp if stamp else datetime.datetime.now().strftime('%H:%M')
            ).classes('w-full').move(chat)
            if clean_message:
                message_input.set_value('')

    Message = message()

    async def refresh_model():
        using_model.set_options(await Message.get_model())
        
    async def submit_message():
        
        if not message_input.value:
            raise ValueError('Text is required')
        
        elif message_input.value == '/config':
            apiPoint.set_value(Message.get_url())
            model_api_key.set_value(Message.get_key())
            config_dialog.open()
            message_input.set_value('')
            return
        
        elif message_input.value == '/light-theme':
            ui.dark_mode(False)
            message_input.set_value('')
            return
        
        elif message_input.value == '/dark-theme':
            ui.dark_mode(True)
            message_input.set_value('')
            return
        
        elif message_input.value == '/print-message':
            print(Message.message)
            message_input.set_value('')
            return
        
        elif message_input.value == '/clear':
            Message.message = []
            chat.clear()
            message_input.set_value('')
            ui.notify('消息已清空', color='positive')
            return
        
        if select_role.value == '助手':
            Message.add(text=message_input.value, role='assistant')
            message_input.set_value('')
            return
        
        if using_model.value == '不使用任何模型':
            Message.send_message(text=message_input.value, clean_message=True)
            return
        
        Message.add(text=message_input.value)
        await Message.generate_response()

    def saveConfig():
        Message.set_url(apiPoint.value)
        Message.set_key(model_api_key.value)
        ui.notify('配置已保存，正在重载端点...', color='positive')
        config_dialog.close()

    with ui.dialog().props('persistent') as config_dialog:
        with ui.card().classes('w-2/3'):
            ui.label('配置').classes('text-2xl text-bold p-2')
            with ui.scroll_area().classes('w-full flex-grow'):
                apiPoint = ui.input('API 地址', value='http://localhost:1234/v1').classes('w-full').props('filled')
                model_api_key = ui.input(label='API Key', placeholder='无需 API Key 请留空').classes('w-full').props('filled')
                model_temperature = ui.number(label='模型温度', value=0.6, min=0, max=1, step=0.1).classes('w-full').props('filled')
                with ui.row(align_items='center').classes('w-full'):
                    using_model = ui.select(options=['不使用任何模型'], label='模型', value='不使用任何模型', new_value_mode='add').classes('flex-grow').props('filled')
                    refreshButton = ui.button(icon='refresh', on_click=refresh_model).props('flat fab-mini').tooltip('从服务端获取模型列表')
                system_prompt = ui.textarea(label='系统提示词', placeholder='不填默认使用兜底提示词，需要清空消息生效').classes('w-full').props('filled')
                with ui.row(align_items='center').classes('w-full justify-between'):
                    ui.label('角色: ')
                    select_role = ui.toggle(options=['用户', '助手'], value='用户')
                
                with ui.row(align_items='center').classes('w-full justify-between'):
                    enable_tts = ui.switch(text='启用语音输出')
                    tts_type = ui.toggle(options=['GPT', 'CosyVoice'], value='CosyVoice')
            with ui.row(align_items='center').classes('w-full'):
                ui.label('* 除特殊说明外所有改动将在下次发送消息时生效').classes('text-gray-500')
                ui.space()
                ui.button('保存并重载端点', on_click=saveConfig).props('rounded')
                                
    with ui.card().classes('absolute-center w-2/3 h-4/5'):
        with ui.row(align_items='center').classes('w-full'):
            ui.label('Message Helper').classes('text-2xl text-bold p-4')

        chat = ui.scroll_area().classes('w-full h-full')
        
        with ui.card().classes('w-full p-2').props('flat'):
            with ui.row(align_items='center').classes('w-full') as thinking:
                ui.spinner()
                ui.label("对方正在输入...").classes('text-gray-500')
            thinking.set_visibility(False)
            message_input = ui.input(label='输入消息...', 
                                    autocomplete=['/config', '/clear-message', '/light-theme', '/dark-theme']) \
                .classes('w-full').props('flat filled stack-label autogrow') \
                .on('keydown.enter', submit_message)
            with ui.row(align_items='center').classes('w-full'):
                tts_speaker = ui.audio(src='about:blank', autoplay=True).bind_visibility_from(enable_tts, 'value')
                ui.space()
                sendButton = ui.button('发送 (Enter)', on_click=submit_message).classes('h-full ml-auto')

ui.run(title='Message Helper', favicon='🤖', reload=False)