// create_zone.go — Create a managed DNS zone via Go SDK
// Usage: go run ./create_zone.go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    dns "cloud.google.com/go/dns/apiv1"
    "cloud.google.com/go/dns/apiv1/dnspb"
    "google.golang.org/api/option"
    "google.golang.org/protobuf/proto"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    if project == "" { log.Fatal("CLOUDSDK_CORE_PROJECT not set") }

    client, err := dns.NewManagedZonesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewManagedZonesRESTClient: %v", err) }
    defer client.Close()

    zoneName := getEnv("DNS_ZONE_NAME", "my-zone")
    dnsName := getEnv("DNS_NAME", "example.com.")
    desc := getEnv("DNS_ZONE_DESCRIPTION", "Zone created by gcp-skills")

    zone := &dnspb.ManagedZone{
        Name:        proto.String(zoneName),
        DnsName:     proto.String(dnsName),
        Description: proto.String(desc),
    }

    req := &dnspb.CreateManagedZoneRequest{
        Parent:      fmt.Sprintf("projects/%s", project),
        ManagedZone: zone,
    }

    resp, err := client.CreateManagedZone(ctx, req)
    if err != nil { log.Fatalf("CreateManagedZone: %v", err) }

    fmt.Printf("Zone created: %s\n", resp.GetName())
    fmt.Printf("Name servers: %v\n", resp.GetNameServers())
}

func getEnv(key, fallback string) string {
    if v := os.Getenv(key); v != "" { return v }
    return fallback
}