import boto3

ec2 = boto3.client('ec2')
ec2Resource = boto3.resource('ec2')

def handler(event, context):
  ec2Id = event['detail']['EC2InstanceId']

  if event['detail-type'] == 'EC2 Instance Launch Successful':
    ec2Info = ec2.describe_instances(InstanceIds=[ec2Id])
    ec2Ip = ec2Info['Reservations'][0]['Instances'][0]['PrivateIpAddress']
    base = 'test'
    baseWild = 'test*'
    # (2)
    workers = ec2.describe_instances(Filters=[
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
        return 'successful, ' + str(workerCount)
