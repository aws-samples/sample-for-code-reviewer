import os, re, json, logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import html
from logger import init_logger

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

"""
generate_report不用手动写，通过以下提示词让Claude写即可：

有这样一段代码：
```
insert report_template.html code here.
```

这个template的效果是不错的，前段应用中，只需替换其中data就能完成报告，他是通过javascript把DOM组织起来的。

现在有个需求，要求写一个python方法def generate_report(title, subtitle, data, template='report_template.html')，读取这个template之后，直接把report的完整的html给return出来，要求这个HTML不能使用JavaScript。
效果上要求所有section默认都是展开的。

你需要模拟template里面javascript的逻辑，通过python3把HTML组织好，然后return。

写成一个function就行了，不用独立更多的方法。
不要用特别的第三方库，例如jinja2等
已经import了os, re, json, logging,html你不用提供这部分的import
"""

def generate_report(title, subtitle, data, template='report_template.html'):
    # 读取模板文件
    with open(template, 'r', encoding='utf-8') as file:
        template = file.read()

    # 提取 CSS 样式
    css_match = re.search(r'<style>(.*?)</style>', template, re.DOTALL)
    css = css_match.group(1) if css_match else ''

    # 创建 HTML 结构
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{html.escape(title)}</title>
        <style>{css}</style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="header-content">
                    <h1 id="main-title">{html.escape(title)}</h1>
                    <div class="detection-date-container">
                        <span id="detection-date">{html.escape(subtitle)}</span>
                    </div>
                </div>
            </header>
            <ul id="report-container" class="issue-list">
    """

    # 生成报告内容
    if not data:
        html_content += '<div class="no-issues">没有发现问题</div>'
    else:
        for rule in data:
            if rule.get('content') and isinstance(rule['content'], list):
                for item in rule['content']:
                    html_content += f"""
                    <li class="issue-item">
                        <div class="issue-header">
                            <span class="issue-header-text">{html.escape(item.get('title', 'Untitled Issue'))}
                            {f" ({html.escape(item['filepath'])})" if item.get('filepath') else ''}</span>
                        </div>
                        <div class="issue-content">
                            <div class="metadata-container">
                    """
                    
                    if item.get('title'):
                        html_content += f'<p><strong>Title:</strong> {html.escape(item["title"])}</p>'
                    if rule.get('rule'):
                        html_content += f'<p><strong>Rule:</strong> {html.escape(rule["rule"])}</p>'
                    if item.get('filepath'):
                        html_content += f'<p><strong>File:</strong> {html.escape(item["filepath"])}</p>'
                    
                    html_content += '</div><div class="content-container">'
                    
                    if item.get('content'):
                        content_parts = re.split(r'(```[\s\S]*?```)', item['content'])
                        for part in content_parts:
                            if part.startswith('```') and part.endswith('```'):
                                lang, code = re.match(r'```(.*?)\n([\s\S]*?)\n```', part).groups()
                                html_content += f'<pre class="code-block"><code class="code-block-content {lang}">{html.escape(code)}</code></pre>'
                            else:
                                html_content += html.escape(part).replace('\n', '<br>')
                    
                    html_content += '</div></div></li>'

    # 关闭 HTML 结构
    html_content += """
            </ul>
        </div>
    </body>
    </html>
    """

    return html_content

def send_mail(message):

    message_data = json.loads(message)
    title = message_data.get('title') 
    subtitle = message_data.get('subtitle') 
    data = message_data.get('data')
    report_url = message_data.get('report_url')
    
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = os.getenv('SMTP_PORT')
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    report_sender = os.getenv('REPORT_SENDER')
    report_receiver = os.getenv('REPORT_RECEIVER')

    filtered_data = [item for item in data if item.get('content') and len(item['content']) > 0]
    html = generate_report(title, subtitle, filtered_data)
    replacement = f'<body><div style="border: 1px dashed gray; padding: 5px;">报告原始地址：<a href="{report_url}" target="_blank">点击打开</a></div>'
    html = re.sub(r'<body>', replacement, html)
      
    msg = MIMEMultipart('alternative')
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    msg['Subject'] = title if title else 'No Title'
    msg['From'] = report_sender
    msg['To'] = report_receiver

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        log.info('Report is sent to mail {}: {}'.format(report_receiver, msg['Subject']))

def lambda_handler(event, context):
    
    log.info(event, extra=dict(label='event'))

    for record in event.get('Records'):
        sns_message = record.get('Sns')
        if sns_message:
            subject = sns_message.get('Subject')
            log.info(f'Got SNS subject: {subject}', extra=dict(subject=subject))
            message = sns_message.get('Message')
            log.info(f'Got SNS message.', extra=dict(sns_message=message))

            message_data = json.loads(message)
            invoker = message_data.get('context', {}).get('invoker')   
            
            if invoker == 'webtool':
                pass # Do nothing
            else:
                # 发送邮件
                send_mail(message)

                # 触发飞书/微信/钉钉的WebHook
                # TODO Write your code here

                # 其他操作
                # TODO Write your code here
