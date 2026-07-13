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

    # 获取线路站点列表 → 站点名映射
    line = api_get('/bus/line!encryptedLineDetail.action', {
        'lineId': '0755-07940-1',
        'cityId': '014',
        'grey_city': 0,
        'cshow': 'busDetail',
        'permission': 0,
    })
    stations = line.get('stations', line.get('stns', []))
    order_to_stn = {s['order']: s['sn'] for s in stations}

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
            'station_name': order_to_stn.get(order, ''),
        })

    approaching.sort(key=lambda x: x['distance'])
    return {
        'approaching': approaching,
        'tip': r.get('tip', {}),
    }

def format_message(info):
    buses = info['approaching']
    top = buses[:2]

    if not top:
        return 'E36 招商澜园方向 | 当前无即将到站的车辆'

    def fmt_time(t):
        return t.replace(':', '：') if t else ''

    def min_text(sec):
        m = sec // 60
        return f'{m}分钟' if m > 0 else '即将到站'

    def stn_label(b):
        return b['station_name'] or f'第{b["order"]}站'

    cur = top[0]
    lines = [f'E36最近车次{fmt_time(cur["arrival_time"])}到，还有{min_text(cur["travel_time"])}，还有{cur["stops_away"]}站，目前{stn_label(cur)}。']

    if len(top) > 1:
        nxt = top[1]
        lines.append(f'下一辆车{fmt_time(nxt["arrival_time"])}到，还有{min_text(nxt["travel_time"])}，还有{nxt["stops_away"]}站，目前{stn_label(nxt)}。')

    return '\n'.join(lines)

def make_subject(info):
    buses = info['approaching']
    if not buses:
        return 'E36|暂无信息|'
    b = buses[0]
    stn = b['station_name'] or f'{b["order"]}'
    t = b['arrival_time'] or f'{b["travel_time"]//60}分'
    return f'E36|{t}|{b["travel_time"]//60}Min|{b["stops_away"]}站|{stn}|'

def push_to_wechat(msg, subject):
    import os, smtplib
    from email.mime.text import MIMEText
    user = os.environ.get('SMTP_USER')
    pwd = os.environ.get('SMTP_PASS')
    if not user or not pwd:
        print('[通知] 未设置 SMTP_USER/SMTP_PASS，仅输出到控制台')
        return
    try:
        m = MIMEText(msg, 'plain', 'utf-8')
        m['Subject'] = subject
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
    subject = make_subject(info)
    print(subject)
    print(msg)
    push_to_wechat(msg, subject)
