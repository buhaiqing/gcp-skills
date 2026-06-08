# API & SDK — Cloud Pub/Sub

## REST API
- Discovery doc: https://pubsub.googleapis.com/$discovery/rest?version=v1
- Base URL: https://pubsub.googleapis.com/v1/
- Projects resource: `projects/{project}`
- Topics resource: `projects/{project}/topics/{topic}`
- Subscriptions resource: `projects/{project}/subscriptions/{subscription}`

## Operations Map

| Goal | REST Method | Python SDK Method | Go SDK Method |
|------|------------|-------------------|---------------|
| Create topic | POST /v1/projects/{p}/topics/{t} | PublisherClient.create_topic() | pubsub.NewClient().CreateTopic() |
| Get topic | GET /v1/projects/{p}/topics/{t} | PublisherClient.get_topic() | pubsub.NewClient().Topic() |
| List topics | GET /v1/projects/{p}/topics | PublisherClient.list_topics() | pubsub.NewClient().Topics() |
| Update topic | PATCH /v1/projects/{p}/topics/{t} | PublisherClient.update_topic() | pubsub.Topic.Update() |
| Delete topic | DELETE /v1/projects/{p}/topics/{t} | PublisherClient.delete_topic() | pubsub.Topic.Delete() |
| Create subscription | POST /v1/projects/{p}/subscriptions/{s} | SubscriberClient.create_subscription() | pubsub.NewClient().CreateSubscription() |
| Get subscription | GET /v1/projects/{p}/subscriptions/{s} | SubscriberClient.get_subscription() | pubsub.NewClient().Subscription() |
| List subscriptions | GET /v1/projects/{p}/subscriptions | SubscriberClient.list_subscriptions() | pubsub.NewClient().Subscriptions() |
| Update subscription | PATCH /v1/projects/{p}/subscriptions/{s} | SubscriberClient.update_subscription() | pubsub.Subscription.Update() |
| Delete subscription | DELETE /v1/projects/{p}/subscriptions/{s} | SubscriberClient.delete_subscription() | pubsub.Subscription.Delete() |
| Publish | POST /v1/projects/{p}/topics/{t}:publish | PublisherClient.publish() | pubsub.Topic.Publish() |
| Pull | POST /v1/projects/{p}/subscriptions/{s}:pull | SubscriberClient.pull() | pubsub.Subscription.Receive() |
| Ack | POST /v1/projects/{p}/subscriptions/{s}:acknowledge | msg.ack() | msg.Ack() |
| Nack | POST /v1/projects/{p}/subscriptions/{s}:modifyAckDeadline (0) | msg.nack() | msg.Nack() |
| Seek snapshot | POST /v1/projects/{p}/subscriptions/{s}:seek | SubscriberClient.seek() | pubsub.Subscription.Seek() |
| Create snapshot | POST /v1/projects/{p}/snapshots/{s} | PublisherClient.create_snapshot() | pubsub.NewClient().CreateSnapshot() |
| Get IAM | GET /v1/{resource}:getIamPolicy | resource.get_iam_policy() | resource.IAM().Policy() |
| Set IAM | POST /v1/{resource}:setIamPolicy | resource.set_iam_policy() | resource.IAM().SetPolicy() |

## Python SDK Code Snippets

### Create Topic
```python
# create_topic.py — REST: POST /v1/projects/{project}/topics/{topic}
import os
from google.cloud import pubsub_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
topic_id = os.environ.get("PUBSUB_TOPIC_ID", "my-topic")

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project, topic_id)
topic = publisher.create_topic(request={"name": topic_path})
print(f"Created topic: {topic.name}")
```

### Describe Topic
```python
# describe_topic.py
import os
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(os.environ["CLOUDSDK_CORE_PROJECT"], "{{user.topic_id}}")
topic = publisher.get_topic(request={"topic": topic_path})
print(f"Name: {topic.name}")
print(f"Retention: {topic.message_retention_duration}")
```

### Publish Message
```python
# publish_message.py
import os
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(os.environ["CLOUDSDK_CORE_PROJECT"], "{{user.topic_id}}")
future = publisher.publish(topic_path, b"{{user.message_data}}", source="python")
message_id = future.result()
print(f"Published message ID: {message_id}")
```

### Publish with Ordering Key
```python
# publish_ordered.py
import os
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(os.environ["CLOUDSDK_CORE_PROJECT"], "{{user.topic_id}}")
future = publisher.publish(topic_path, b"{{user.message_data}}", ordering_key="{{user.ordering_key}}")
message_id = future.result()
print(f"Published ordered message ID: {message_id}")
```

### Pull Messages
```python
# pull_messages.py
import os
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(os.environ["CLOUDSDK_CORE_PROJECT"], "{{user.subscription_id}}")
response = subscriber.pull(subscription=subscription_path, max_messages=10)
for msg in response.received_messages:
    print(f"ID: {msg.message.message_id}, Data: {msg.message.data.decode()}, Time: {msg.message.publish_time}")
    subscriber.acknowledge(subscription=subscription_path, ack_ids=[msg.ack_id])
```

### Streaming Pull
```python
# streaming_pull.py
import os
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(os.environ["CLOUDSDK_CORE_PROJECT"], "{{user.subscription_id}}")

def callback(message):
    print(f"Received: {message.data.decode()}")
    message.ack()

streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
print(f"Listening on {subscription_path}...")
try:
    streaming_pull_future.result(timeout=60)
except TimeoutError:
    streaming_pull_future.cancel()
```

### Create Subscription with DLQ
```python
# create_sub_with_dlq.py
import os
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import DeadLetterPolicy, RetryPolicy

subscriber = pubsub_v1.SubscriberClient()
project = os.environ["CLOUDSDK_CORE_PROJECT"]
sub_path = subscriber.subscription_path(project, "{{user.subscription_id}}")
topic_path = subscriber.topic_path(project, "{{user.topic_id}}")
dlq_path = subscriber.topic_path(project, "{{user.dead_letter_topic}}")

subscription = subscriber.create_subscription(
    request={
        "name": sub_path,
        "topic": topic_path,
        "dead_letter_policy": DeadLetterPolicy(dead_letter_topic=dlq_path, max_delivery_attempts=5),
        "retry_policy": RetryPolicy(minimum_backoff="10s", maximum_backoff="600s"),
    }
)
print(f"Created subscription with DLQ: {subscription.name}")
```

### Create Snapshot
```python
# create_snapshot.py
import os
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
project = os.environ["CLOUDSDK_CORE_PROJECT"]
snapshot_path = publisher.snapshot_path(project, "{{user.snapshot_id}}")
sub_path = publisher.subscription_path(project, "{{user.subscription_id}}")

snapshot = publisher.create_snapshot(request={"name": snapshot_path, "subscription": sub_path})
print(f"Created snapshot: {snapshot.name}, expires: {snapshot.expire_time}")
```

### Seek to Snapshot
```python
# seek_snapshot.py
import os
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
project = os.environ["CLOUDSDK_CORE_PROJECT"]
sub_path = subscriber.subscription_path(project, "{{user.subscription_id}}")
snapshot_path = subscriber.snapshot_path(project, "{{user.snapshot_id}}")

response = subscriber.seek(request={"subscription": sub_path, "snapshot": snapshot_path})
print(f"Seek completed: {response}")
```

## Go SDK Code Snippets

### Create Topic
```go
// create_topic.go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "cloud.google.com/go/pubsub"
)

func main() {
    ctx := context.Background()
    client, err := pubsub.NewClient(ctx, os.Getenv("CLOUDSDK_CORE_PROJECT"))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    topic, err := client.CreateTopic(ctx, "{{user.topic_id}}")
    if err != nil { log.Fatalf("CreateTopic: %v", err) }
    fmt.Printf("Created topic: %s\n", topic.ID())
}
```

### Publish Message
```go
// publish_message.go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "cloud.google.com/go/pubsub"
)

func main() {
    ctx := context.Background()
    client, err := pubsub.NewClient(ctx, os.Getenv("CLOUDSDK_CORE_PROJECT"))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    topic := client.Topic("{{user.topic_id}}")
    result := topic.Publish(ctx, &pubsub.Message{Data: []byte("{{user.message_data}}")})
    id, err := result.Get(ctx)
    if err != nil { log.Fatalf("Publish: %v", err) }
    fmt.Printf("Published message ID: %s\n", id)
}
```

### Pull Messages
```go
// pull_messages.go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "cloud.google.com/go/pubsub"
)

func main() {
    ctx := context.Background()
    client, err := pubsub.NewClient(ctx, os.Getenv("CLOUDSDK_CORE_PROJECT"))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    sub := client.Subscription("{{user.subscription_id}}")
    err = sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
        fmt.Printf("Received: %s\n", string(msg.Data))
        msg.Ack()
    })
    if err != nil { log.Fatalf("Receive: %v", err) }
}
```

### Create Subscription with DLQ
```go
// create_sub_dlq.go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "time"
    "cloud.google.com/go/pubsub"
)

func main() {
    ctx := context.Background()
    client, err := pubsub.NewClient(ctx, os.Getenv("CLOUDSDK_CORE_PROJECT"))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    topic := client.Topic("{{user.topic_id}}")
    cfg := pubsub.SubscriptionConfig{
        Topic:            topic,
        AckDeadline:      10 * time.Second,
        RetentionDuration: 7 * 24 * time.Hour,
        DeadLetterPolicy: &pubsub.DeadLetterPolicy{
            DeadLetterTopic:     "projects/{{env.CLOUDSDK_CORE_PROJECT}}/topics/{{user.dead_letter_topic}}",
            MaxDeliveryAttempts: 5,
        },
        RetryPolicy: &pubsub.RetryPolicy{
            MinimumBackoff: 10 * time.Second,
            MaximumBackoff: 600 * time.Second,
        },
    }
    sub, err := client.CreateSubscription(ctx, "{{user.subscription_id}}", cfg)
    if err != nil { log.Fatalf("CreateSubscription: %v", err) }
    fmt.Printf("Created subscription: %s\n", sub.ID())
}
```

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Topic details | $.{name,messageRetentionDuration,kmsKeyName,schemaSettings} | Topic config |
| Subscription details | $.{name,topic,ackDeadlineSeconds,messageRetentionDuration,pushConfig,deadLetterPolicy,retryPolicy,enableMessageOrdering,enableExactlyOnceDelivery,expirationPolicy} | Subscription config |
| List topics | $.[].{name,messageRetentionDuration} | Topic list |
| List subscriptions | $.[].{name,topic,ackDeadlineSeconds,pushConfig} | Subscription list |
| Publish response | $.messageIds[] | Published message IDs |
| Pull response | $.[].{ackId,message.data,message.messageId,message.publishTime,message.attributes} | Pulled messages |
| Snapshot details | $.{name,subscription,expireTime} | Snapshot config |
| DLQ policy | $.deadLetterPolicy.{deadLetterTopic,maxDeliveryAttempts} | DLQ config |
| Retry policy | $.retryPolicy.{minimumBackoff,maximumBackoff} | Retry config |
| IAM policy | $.{bindings[],etag,version} | IAM bindings |
