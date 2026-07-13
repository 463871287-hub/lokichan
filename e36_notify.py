"""
E36 龙华→南山 招商澜园 到站提醒脚本
在 Windows 任务计划程序中设置为每天 6:30 运行
输出格式化的消息用于 WeChat 推送
"""

import sys
sys.path.insert(0, '.')
from chelaile_api import api_get, json

def get_arrival_info():
    r = api_get('/bus/line!encryptedBusDetail.action', {
        'lineId': '0755-07940-1',
        'targetOrder': 13,
        'specialTargetOrder': 13,
        'specail': 0,
        'stationId': '0755-11919',
        'cshow': 'busDetail',
    })

    buses = r.get('buses', [])
    approaching = []

    for bus in buses:
        order = bus.get('order', 0)
        dist = bus.get('distanceToWaitStn', -1)
        bus_id = bus.get('busId', '').lstrip('\u7ca4')
        travels = bus.get('travels', [])

        if dist < 0:
            continue

        travel = travels[0] if travels else {}
        recomm_tip = travel.get('recommTip', '')
        travel_time = travel.get('travelTime', -1)

        approaching.append({
            'bus_id': bus_id,
            'order': order,
            'distance': dist,
            'arrival_time': recomm_tip,
            'travel_time': travel_time,
            'stops_away': 13 - order,
        })

    approaching.sort(key=lambda x: x['distance'])
    return {
        'approaching': approaching,
        'tip': r.get('tip', {}),
    }

def format_message(info):
    buses = info['approaching']
    tip = info.get('tip', {})

    if not buses:
        return 'E36 (龙华→南山) 招商澜园 | 当前无即将到站的车辆'

    lines = ['E36 (龙华→南山) → 招商澜园']
    for b in buses:
        parts = [f'{b["bus_id"]}']
        if b['arrival_time']:
            parts.append(f'预计 {b["arrival_time"]} 到')
        elif b['travel_time'] > 0:
            mins = b['travel_time'] // 60
            parts.append(f'约 {mins} 分钟')
        if b['stops_away'] > 0:
            parts.append(f'还有 {b["stops_away"]} 站')
        if b['distance'] > 0 and b['distance'] < 50000:
            parts.append(f'距本站 {b["distance"]//1000}.{b["distance"]%1000//100}km')
        lines.append('  '.join(parts))

    return ' | '.join(lines)

def push_to_wechat(msg):
    import os, smtplib
    from email.mime.text import MIMEText
    user = os.environ.get('SMTP_USER')
    pwd = os.environ.get('SMTP_PASS')
    if not user or not pwd:
        print('[通知] 未设置 SMTP_USER/SMTP_PASS，仅输出到控制台')
        return
    try:
        m = MIMEText(msg, 'plain', 'utf-8')
        m['Subject'] = 'E36到站提醒'
        m['From'] = user
        m['To'] = user
        s = smtplib.SMTP_SSL('smtp.qq.com', 465)
        s.login(user, pwd)
        s.send_message(m)
        s.quit()
        print('[通知] 已发送邮件到QQ邮箱')
    except Exception as e:
        print(f'[通知] 发送失败: {e}')

if __name__ == '__main__':
    info = get_arrival_info()
    msg = format_message(info)
    print(msg)
    push_to_wechat(msg)
