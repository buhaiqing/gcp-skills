# gcloud — Cloud Storage CLI

## CLI Convention (Dual-Path)

This skill uses **two CLI tools**, both part of the Google Cloud SDK:

| Tool | Primary For | Notes |
|------|-------------|-------|
| **`gcloud storage`** | Bucket-level operations | Newer CLi; create, describe, list, update, delete buckets, IAM, lifecycle, CORS, notifications |
| **`gsutil`** | Object-level operations | Traditional tool; cp, mv, rsync, rm, ls, cat, stat, compose, signurl, hash, acl, setmeta |

Both tools work against the same API and are fully interoperable.

## Command Map: Buckets (gcloud storage)

| Goal | gcloud command |
|------|---------------|
| Create | gcloud storage buckets create gs://B --location=L --default-storage-class=C --uniform-bucket-level-access --format=json |
| Describe | gcloud storage buckets describe gs://B --format=json |
| List | gcloud storage buckets list --project=P --format=json |
| Update labels | gcloud storage buckets update gs://B --update-labels=K=V --format=json |
| Update versioning | gcloud storage buckets update gs://B --versioning --format=json |
| Update retention | gcloud storage buckets update gs://B --retention-period=S --format=json |
| Lock retention | gcloud storage buckets update gs://B --lock-retention-period --format=json |
| Remove retention | gcloud storage buckets update gs://B --remove-retention-policy --format=json |
| Update encryption | gcloud storage buckets update gs://B --default-encryption-key=K --format=json |
| Clear encryption | gcloud storage buckets update gs://B --clear-default-encryption-key --format=json |
| Update CORS | gcloud storage buckets update gs://B --cors-file=F --format=json |
| Enable Autoclass | gcloud storage buckets update gs://B --autoclass --format=json |
| Disable Autoclass | gcloud storage buckets update gs://B --no-autoclass --format=json |
| Set lifecycle | gcloud storage buckets update gs://B --lifecycle-file=F --format=json |
| Add IAM binding | gcloud storage buckets add-iam-policy-binding gs://B --member=M --role=R --format=json |
| Remove IAM binding | gcloud storage buckets remove-iam-policy-binding gs://B --member=M --role=R --format=json |
| Get IAM policy | gcloud storage buckets get-iam-policy gs://B --format=json |
| Delete bucket | gcloud storage buckets delete gs://B |

## Command Map: Objects (gsutil + gcloud storage)

| Goal | Command |
|------|---------|
| Upload file | gsutil cp FILE gs://B/O |
| Upload with storage class | gsutil cp -s CLASS FILE gs://B/O |
| Download object | gsutil cp gs://B/O ./local |
| Download version | gsutil cp gs://B/O#VERSION ./local |
| Copy object | gsutil cp gs://B1/O1 gs://B2/O2 |
| Move object | gsutil mv gs://B1/O1 gs://B2/O2 |
| List objects | gsutil ls gs://B/[PREFIX] |
| List objects (detailed) | gsutil ls -l gs://B/ |
| List with versions | gcloud storage objects list gs://B --all-versions --format=json |
| Delete object | gsutil rm gs://B/O |
| Stat object | gsutil stat gs://B/O |
| Compose objects | gsutil compose gs://B/O1 gs://B/O2 gs://B/ODEST |
| Generate signed URL | gsutil signurl -d DURATION KEY gs://B/O |
| Compute hash | gsutil hash -m FILE |

## CLI vs API Coverage

| Operation | gcloud storage | gsutil | Notes |
|-----------|---------------|--------|-------|
| Bucket CRUD | ✅ | ❌ | gcloud storage preferred |
| Object CRUD | ✅ | ✅ | gsutil preferred for cp/mv/rm |
| Object compose | ❌ | ✅ | gsutil only |
| Signed URL | ❌ | ✅ | gsutil signurl |
| Bucket IAM | ✅ | ❌ | gcloud storage add-iam-policy-binding |
| Lifecycle | ✅ | ❌ | gcloud storage update --lifecycle-file |
| Retention | ✅ | ❌ | gcloud storage update --retention-period |
| Lock retention | ✅ | ❌ | gcloud storage update --lock-retention-period |
| CORS | ✅ | ❌ | gcloud storage update --cors-file |
| Notifications | ✅ | ✅ | gcloud storage notifications * |
| Object holds | ❌ | ✅ | gsutil retention * |
| Requester Pays | ✅ | ✅ | gcloud storage buckets update --requester-pays / gsutil -u U |