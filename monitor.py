import boto3
import os
import requests
import json

ec2 = boto3.client('ec2')

def handler(event, context):
  ec2Id = event['detail']['EC2InstanceId']

  if event['detail-type'] == 'EC2 Instance Launch Successful':
    ec2Info = ec2.describe_instances(InstanceIds=[ec2Id])
    ec2Ip = ec2Info['Reservations'][0]['Instances'][0]['PrivateIpAddress']
    loadBalancer = switch_account_to_internal()

    if addEC2Instance(ec2Ip, loadBalancer):
      sendSlackMessage(findEC2Name(ec2Info), ec2Ip, True)
  elif event['detail-type'] == 'EC2 Instance Terminate Successful':
    autoScaling = boto3.client('autoscaling')
    autoScalingInfo = autoScaling.describe_auto_scaling_groups(AutoScalingGroupNames=[
      'group name'
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

  return 'successful'

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
    aws_access_key_id=os.environ['BASIC_ACCOUNT_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['BASIC_ACCOUNT_SECRET_ACCESS_KEY']
  )

def sendSlackMessage(nameOfInstance, ip, didCreate):
  headers = {
    'Content-type': 'application/json'
  }
  with open('slack_payload.json') as f:
    slackPayload = json.load(f)

  if didCreate:
    slackPayload['text'] = 'Autoscaling Event Captured - Target Created :white_check_mark:'
    slackPayload['attachments'][0]['blocks'][0]['text']['text'] = '*Cluster:* name \n *Instance:* `%s` \n *IP:* `%s`' %(nameOfInstance, ip)
  else:
    slackPayload['text'] = 'Autoscaling Event Captured - Target Deleted :downvote:'
    slackPayload['attachments'][0]['blocks'][0]['text']['text'] = '*Cluster:* name \n *Instance:* `%s` \n *IP:* `%s`' %(nameOfInstance, ip)


  print 'Sending slack message'
  r = requests.post(url=os.environ['SLACK_ENDPOINT'], data=json.dumps(slackPayload), headers=headers)
  print 'Slack response: %s' % str(r)

  # (4) Bamboo Call Using Requests
  BAMBOO_USERPASS = os.environ['BAMBOO_USERPASS']
  url = os.environ['URL']
  HEADERS = {'Authorization':'Basic `%s`'% BAMBOO_USERPASS}
  print 'Sending api call to `%s`'% url
  response = requests.Get(url,headers=HEADERS)
  content = response.content
  print 'Call sent, response: `%s`'% content

# 1. Set base to clustername-worker.
# 2. Get the array of all instances with a name tag containing the base.
# 3. For each instance id in the array, edit the name tag.
# 4. Make an api call to trigger script to update shared ssh configs...
# This will keep cluster instances seamlessly accessible via even while autoscaling is ongoing.

def findEC2Name(ec2Info):
  renameWorkers
  tags = ec2Info['Reservations'][0]['Instances'][0]['Tags']
  # (1)
  for tag in tags:
    if tag['Key'] == 'Name':
      return tag['Value']

def renameWorkers():
  base = 'clustername-worker'
  baseWild = 'clustername-worker*'
  # (2)
  workers = ec2.describe_instances(Filters=[
    {
      'Name': 'tag:Name',
      'Values':
        [
          baseWild
        ]
    }
  ]) # %(baseWild)
  # (3)
  for worker in workers["Reservations"]:
    for instance in worker["Instances"]:
      instanceID = ec2Resource.Instance(instance["InstanceId"])
      i = 0
      #  for i in range(workerCount)
      for i in range(len(workers["Reservations"])):
        custom = base + str(i)
        ec2.create_tags(DryRun=True, Resources=instanceID, Tags=[{
          'Key': 'Name',
          'Value': custom
        }])
        i+=1

  # Rename EC2 in different class.
  # Old: findEC2Name(ec2Info)
  # The given ec2Id passes through the instance id...
  # ... from the event.
  # ec2Info runs describe instances against the above id.
  # findEC2Name then gets the tags from the json returned from...
  # ... ec2Info, and for each instance it will return the Name.
