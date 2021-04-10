import yaml
import os
import requests
from datetime import datetime
import threading
from operator import itemgetter
import dateutil.parser

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
payloads = []
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
            embed = {
                'title': maintenance['name'],
                'url': 'https://status.rubellite.ml',
                'footer': {'text': 'Status Relay Daemon', 'icon_url': 'https://static.rubellite.ml/community.png'},
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

events = {'maintenance': threading.Event()}
jobs = {'maintenance': ThreadJob(check_for_maintenance, events['maintenance'], 15)}
check_for_maintenance()
jobs['maintenance'].start()

print('Status update checker is now operational.')
