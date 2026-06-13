// create_network.go — Create a VPC network via Go SDK
// Usage: go run ./create_network.go
package main

import (
    "context"
    "fmt"
    "os"

    compute "cloud.google.com/go/compute/apiv1"
    "cloud.google.com/go/compute/apiv1/computepb"
    "google.golang.org/api/option"
    "google.golang.org/protobuf/proto"
)

func main() {
    ctx := context.Background()
    client, err := compute.NewNetworksRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        panic(err)
    }
    defer client.Close()

    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    req := &computepb.InsertNetworkRequest{
        Project: project,
        NetworkResource: &computepb.Network{
            Name:                  proto.String(getEnv("VPC_NETWORK_NAME", "my-network")),
            AutoCreateSubnetworks: proto.Bool(false),
            RoutingConfig: &computepb.NetworkRoutingConfig{
                RoutingMode: proto.String("GLOBAL"),
            },
        },
    }
    op, err := client.Insert(ctx, req)
    if err != nil { panic(err) }
    if err := op.Wait(ctx); err != nil { panic(err) }
    fmt.Printf("Created: %s\n", op.Proto().GetTargetLink())
}

func getEnv(key, fallback string) string {
    if v := os.Getenv(key); v != "" { return v }
    return fallback
}