import yaml
import os
import requests
from datetime import datetime
import threading
from operator import itemgetter
import dateutil.parser
from termcolor import cprint

with open(os.path.join(os.path.dirname(__file__), '../config.yaml')) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

class ThreadJob(threading.Thread):
    def __init__(self, callback, event, interval):
        self.callback = callback
        self.event = event
        self.interval = interval
        super(ThreadJob, self).__init__()

    def run(self):
        while not self.event.wait(self.interval):
            self.callback()

ids = []
message_ids = []

def check_for_maintenance():
    r = requests.get(f'https://api.instatus.com/v1/{config["instatus"]["page_id"]}/maintenances', headers={'Authorization': f'Bearer {config["instatus"]["api_token"]}'}).json()
    if len(r) > 0:
        def format_field(update):
            if update['status'] == 'COMPLETED':
                return f'**<:status_online:589592485517590532> All Systems Operational** ({dateutil.parser.isoparse(update["createdAt"]).strftime("%I:%M %p")})', 0x27b17a
            elif update['status'] == 'INPROGRESS':
                return f'**<:idle:732025087896715344> Ongoing Maintenance** ({dateutil.parser.isoparse(update["createdAt"]).strftime("%I:%M %p")})', 0xffd100
            elif update['status'] == 'NOTSTARTEDYET':
                return f'**<:iconclock:811925897036038165> Scheduled Maintenance** ({dateutil.parser.isoparse(update["started"]).strftime("%I:%M %p")})', 0xff595c

        for maintenance in r:
            completed = False
            for update in maintenance['updates']:
                if update['status'] == 'COMPLETED':
                    completed = True
            if completed == True:
                break
            
            embed = {
                'title': maintenance['name'],
                'url': f'https://peach.instatus.com/{maintenance["id"]}',
                'footer': {'text': 'Status Relay Daemon', 'icon_url': 'https://res.cloudinary.com/sup/image/upload/v1618877889/dphc4qr0yixi8giinrzt.png'},
                'fields': [],
                'timestamp': str(datetime.now())
            }

            sorted_updates = sorted(maintenance['updates'], key=itemgetter('createdAt'))
            new = 0

            for update in sorted_updates:
                field, colour = format_field(update)
                embed['fields'].append({'name': field, 'value': update['message']})
                embed['color'] = colour
                if (update['id'] not in ids):
                    new = new + 1

            if maintenance['id'] not in ids:
                message = requests.post(f'https://discord.com/api/webhooks/{config["webhook"]["id"]}/{config["webhook"]["token"]}?wait=true', json={'embeds': [embed], 'content': '<@&795660890925432902>'})
                message_ids.append({'id': maintenance['id'], 'message_id': message.json()['id']})
                
                for update in maintenance['updates']:
                    ids.append(update['id'])
                ids.append(maintenance['id'])
            elif new > 0:
                message_id = None
                for entry in message_ids:
                    if entry['id'] == maintenance['id']:
                        message_id = entry['message_id']

                requests.patch(f'https://discord.com/api/webhooks/{config["webhook"]["id"]}/{config["webhook"]["token"]}/messages/{message_id}', json={'embeds': [embed]})
                if maintenance['updates'][-1]['status'] == 'RESOLVED':
                    ids.remove(maintenance['id'])
                    for update in maintenance:
                        ids.remove(update['id'])

def check_for_incidents():
    r = requests.get(f'https://api.instatus.com/v1/{config["instatus"]["page_id"]}/incidents', headers={'Authorization': f'Bearer {config["instatus"]["api_token"]}'}).json()
    if len(r) > 0:
        def format_field(update):
            if update['status'] == 'RESOLVED':
                return f'**<:status_online:589592485517590532> All Systems Operational** ({dateutil.parser.isoparse(update["createdAt"]).strftime("%I:%M %p")})', 0x27b17a, 'https://static.rubellite.ml/status/resolved.png'
            elif update['status'] == 'MONITORING':
                return f'**<:zep_idle:665908128331726848> Monitoring** ({dateutil.parser.isoparse(update["createdAt"]).strftime("%I:%M %p")})', 0xffd100, 'https://static.rubellite.ml/status/monitoring.png'
            elif update['status'] == 'IDENTIFIED':
                return f'**🔍 Identified** ({dateutil.parser.isoparse(update["createdAt"]).strftime("%I:%M %p")})', 0xff595c, 'https://static.rubellite.ml/status/identified.png'
            elif update['status'] == 'INVESTIGATING':
                return f'**🔍 Investigating** ({dateutil.parser.isoparse(update["createdAt"]).strftime("%I:%M %p")})', 0xff595c, 'https://static.rubellite.ml/status/investigating.png'

        for incident in r:
            completed = False
            for update in incident['updates']:
                if update['status'] == 'COMPLETED':
                    completed = True
            if completed == True:
                break

            embed = {
                'title': incident['name'],
                'url': f'https://peach.instatus.com/{incident["id"]}',
                'footer': {'text': 'Status Relay Daemon', 'icon_url': 'https://res.cloudinary.com/sup/image/upload/v1618877889/dphc4qr0yixi8giinrzt.png'},
                'fields': [],
                'timestamp': str(datetime.now())
            }

            sorted_updates = sorted(incident['updates'], key=itemgetter('createdAt'))
            new = 0

            for update in sorted_updates:
                field, colour, thumbnail = format_field(update)
                embed['fields'].append({'name': field, 'value': update['message']})
                embed['color'] = colour
                embed['thumbnail'] = {'url': thumbnail}
                if (update['id'] not in ids):
                    new = new + 1

            if incident['id'] not in ids:
                message = requests.post(f'https://discord.com/api/webhooks/{config["webhook"]["id"]}/{config["webhook"]["token"]}?wait=true', json={'embeds': [embed], 'content': '<@&795660890925432902>'})
                message_ids.append({'id': incident['id'], 'message_id': message.json()['id']})
                
                for update in incident['updates']:
                    ids.append(update['id'])
                ids.append(incident['id'])
            elif new > 0:
                message_id = None
                for entry in message_ids:
                    if entry['id'] == incident['id']:
                        message_id = entry['message_id']

                requests.patch(f'https://discord.com/api/webhooks/{config["webhook"]["id"]}/{config["webhook"]["token"]}/messages/{message_id}', json={'embeds': [embed]})
                if incident['updates'][-1]['status'] == 'RESOLVED':
                    ids.remove(incident['id'])
                    for update in incident:
                        ids.remove(update['id'])

cprint('Instantiating jobs...', 'yellow', attrs=['blink'])
jobs = {
    'maintenance': ThreadJob(check_for_maintenance, threading.Event(), 15),
    'incidents': ThreadJob(check_for_incidents, threading.Event(), 15)
}
cprint('Checking for maintenance...', 'yellow', attrs=['blink'])
check_for_maintenance()
cprint('Checking for incidents...', 'yellow', attrs=['blink'])
check_for_incidents()
jobs['maintenance'].start()
jobs['incidents'].start()

cprint('Status Relay is now live.', 'green', attrs=['blink'])