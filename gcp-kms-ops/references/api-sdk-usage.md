# API & SDK — Cloud KMS

## REST API
- Discovery doc: https://cloudkms.googleapis.com/$discovery/rest?version=v1
- Base URL: https://cloudkms.googleapis.com/v1/

## Operations Map

| Goal | REST Method | Go SDK Method |
|------|------------|---------------|
| Create key ring | POST parent/keyRings | KeyManagementClient.CreateKeyRing |
| List key rings | GET parent/keyRings | KeyManagementClient.ListKeyRings |
| Create key | POST parent/cryptoKeys | KeyManagementClient.CreateCryptoKey |
| Get key | GET {key_name} | KeyManagementClient.GetCryptoKey |
| List keys | GET parent/cryptoKeys | KeyManagementClient.ListCryptoKeys |
| Update key | PATCH {key_name} | KeyManagementClient.UpdateCryptoKey |
| List key versions | GET parent/cryptoKeyVersions | KeyManagementClient.ListCryptoKeyVersions |
| Get key version | GET {version_name} | KeyManagementClient.GetCryptoKeyVersion |
| Destroy version | POST {version_name}:destroy | KeyManagementClient.DestroyCryptoKeyVersion |
| Restore version | POST {version_name}:restore | KeyManagementClient.RestoreCryptoKeyVersion |
| Enable version | POST {version_name}:enable | KeyManagementClient.EnableCryptoKeyVersion |
| Disable version | POST {version_name}:disable | KeyManagementClient.DisableCryptoKeyVersion |
| Encrypt | POST {key_name}:encrypt | KeyManagementClient.Encrypt |
| Decrypt | POST {key_name}:decrypt | KeyManagementClient.Decrypt |

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create key ring | $.{name,createTime} | Key ring details |
| List key rings | $.keyRings[].{name,createTime} | Key ring list |
| Create key | $.{name,primary,purpose} | Key details |
| Describe key | $.{name,primary,rotationPeriod,labels} | Key config |
| List keys | $.cryptoKeys[].{name,primary,purpose} | Key list |
| Describe key version | $.{name,state,protectionLevel,algorithm} | Version details |
| Encrypt | $.{name,ciphertext} | Encrypted data |
| Decrypt | $.{plaintext} | Decrypted data |