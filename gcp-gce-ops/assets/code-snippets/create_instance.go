// create_instance.go — Create a GCE VM instance via Go SDK
// Usage: go run ./create_instance.go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    
    compute "cloud.google.com/go/compute/apiv1"
    "cloud.google.com/go/compute/apiv1/computepb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    zone := os.Getenv("CLOUDSDK_COMPUTE_ZONE")
    if zone == "" { zone = "us-central1-a" }
    instanceName := os.Getenv("GCE_INSTANCE_NAME")
    if instanceName == "" { instanceName = "my-instance" }
    
    client, err := compute.NewInstancesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("NewInstancesRESTClient: %v", err)
    }
    defer client.Close()
    
    req := &computepb.InsertInstanceRequest{
        Project: project,
        Zone:    zone,
        InstanceResource: &computepb.Instance{
            Name: protoPtr(instanceName),
            MachineType: protoPtr(fmt.Sprintf("projects/%s/zones/%s/machineTypes/n2-standard-2", project, zone)),
            Disks: []*computepb.AttachedDisk{{
                Boot: protoBool(true),
                InitializeParams: &computepb.AttachedDiskInitializeParams{
                    SourceImage: protoPtr("projects/debian-cloud/global/images/family/debian-12"),
                    DiskSizeGb:  protoInt64(20),
                    DiskType:    protoPtr(fmt.Sprintf("projects/%s/zones/%s/diskTypes/pd-balanced", project, zone)),
                },
            }},
            NetworkInterfaces: []*computepb.NetworkInterface{{
                Name: protoPtr("default"),
            }},
        },
    }
    
    op, err := client.Insert(ctx, req)
    if err != nil { log.Fatalf("Insert: %v", err) }
    if err := op.Wait(ctx); err != nil { log.Fatalf("Wait: %v", err) }
    fmt.Println("Created instance:", instanceName)
}

func protoPtr(s string) *string { return &s }
func protoBool(b bool) *bool { return &b }
func protoInt64(i int64) *int64 { return &i }
