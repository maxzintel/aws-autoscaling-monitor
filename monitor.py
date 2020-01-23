import boto3
import os
import requests
import json

ec2 = boto3.client('ec2')
ec2Resource = boto3.resource('ec2')

def handler(event, context):
  ec2Id = event['detail']['EC2InstanceId']
  base = 'clustername-worker-'
  baseWild = 'clustername-worker-*'
  matched = ec2.describe_instances(Filters=[
    {
      'Name': 'tag:Name',
      'Values':
        [
          baseWild
        ]
    }
  ])

  workerCount = len(matched["Reservations"])
  for i in range(0, workerCount):
    for instanceObj in matched["Reservations"]:
      instanceID = str(instanceObj["Instances"][0]["InstanceId"])
      custom = base + str(i)
      ec2.create_tags(
        DryRun=False,
        Resources=[
          instanceID
        ],
        Tags=[
          {
            'Key': 'Name',
            'Value': str(custom)
          }
        ]
      )
      i+=1
    else:
      if event['detail-type'] == 'EC2 Instance Launch Successful':
        ec2Info = ec2.describe_instances(InstanceIds=[ec2Id])
        ec2Ip = ec2Info['Reservations'][0]['Instances'][0]['PrivateIpAddress']
        loadBalancer = switch_account_to_internal()

        if addEC2Instance(ec2Ip, loadBalancer):
          sendSlackMessage(findEC2Name(ec2Info), ec2Ip, True)
      elif event['detail-type'] == 'EC2 Instance Terminate Successful':
        autoScaling = boto3.client('autoscaling')
        autoScalingInfo = autoScaling.describe_auto_scaling_groups(AutoScalingGroupNames=[
          'clustername-worker terraform-xxx'
          ]
        )
        currentInstancesInfo = autoScalingInfo['AutoScalingGroups'][0]['Instances']
        currentInstances = []
        for i in range(len(currentInstancesInfo)):
          currentInstances.append(currentInstancesInfo[i]['InstanceId'])

        ec2Info = ec2.describe_instances(InstanceIds=currentInstances)
        ec2Ips = []

        for ec2Instances in ec2Info['Reservations']:
          for value in ec2Instances['Instances']:
            ec2Ips.append(value['PrivateIpAddress'])

        loadBalancer = switch_account_to_internal()

        targetGroupHealthHTTP = loadBalancer.describe_target_health(TargetGroupArn=json.loads(os.environ['ARN_TARGET_GROUPS'])[0]['arn'])
        targetGroupIps = []

        for value in targetGroupHealthHTTP['TargetHealthDescriptions']:
          targetGroupIps.append(value['Target']['Id'])

        notMatchingIps = list(set(targetGroupIps) - set(ec2Ips))

        for ip in notMatchingIps:
          if removeFromTargetGroup(ip, loadBalancer):
            try:
              sendSlackMessage(findEC2Name(ec2.describe_instances(InstanceIds=[ec2Id])), ip, False)
            except:
              sendSlackMessage('Could not find name', ip, False)
      user = os.environ['user']
      passw = os.environ['passw']
      url = os.environ['URL']
      HEADERS = {'Content-Type':'application/json'}
      print 'Sending api call to `%s`'% url
      post = requests.post(url, headers=HEADERS, auth=(user, passw))
      content = post.content
      print(post.status_code)
      print 'Call sent, response: `%s`'% content
      return 'successful, worker tags edited: ' + str(workerCount)

def addEC2Instance(ip, loadBalancer):
  targetGroups = json.loads(os.environ['ARN_TARGET_GROUPS'])
  successCounter = 0
  for targetGroup in targetGroups:
    target = [
      {
        'Id': ip,
        'Port': targetGroup['port'],
        'AvailabilityZone': 'all'
      }
    ]
    response = loadBalancer.register_targets(
      TargetGroupArn=targetGroup['arn'],
      Targets=target
    )
    print 'Added target: %s' % str(response)
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
      successCounter += 1

  if successCounter == len(targetGroups):
    return True
  return False

def removeFromTargetGroup(ip, loadBalancer):
  targetGroups = json.loads(os.environ['ARN_TARGET_GROUPS'])
  successCounter = 0
  for targetGroup in targetGroups:
    target = [
      {
        'Id': ip,
        'Port': targetGroup['port'],
        'AvailabilityZone': 'all'
      }
    ]
    response = loadBalancer.deregister_targets(
      TargetGroupArn=targetGroup['arn'],
      Targets=target
    )
    print 'Removed target: %s' % str(response)
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
      successCounter += 1

  if successCounter == len(targetGroups):
    return True
  return False

def switch_account_to_internal():
  return boto3.client(
    'elbv2',
    aws_access_key_id=os.environ['ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['SECRET_ACCESS_KEY']
  )

def sendSlackMessage(nameOfInstance, ip, didCreate):
  headers = {
    'Content-type': 'application/json'
  }
  with open('slack_payload.json') as f:
    slackPayload = json.load(f)

  if didCreate:
    slackPayload['text'] = ':aws: Autoscaling Event Captured - Target Created :white_check_mark:'
    slackPayload['attachments'][0]['blocks'][0]['text']['text'] = '*Cluster:* clustername \n *Instance:* `%s` \n *IP:* `%s`' %(nameOfInstance, ip)
  else:
    slackPayload['text'] = ':aws: Autoscaling Event Captured - Target Deleted :downvote:'
    slackPayload['attachments'][0]['blocks'][0]['text']['text'] = '*Cluster:* clustername \n *Instance:* `%s` \n *IP:* `%s`' %(nameOfInstance, ip)

  print 'Sending slack message'
  r = requests.post(url=os.environ['SLACK_ENDPOINT'], data=json.dumps(slackPayload), headers=headers)
  print 'Slack response: %s' % str(r)

def findEC2Name(ec2Info):
  tags = ec2Info['Reservations'][0]['Instances'][0]['Tags']

  for tag in tags:
    if tag['Key'] == 'Name':
      return tag['Value']
