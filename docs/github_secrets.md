# GitHub Secrets Configuration Guide

This guide documents all required GitHub Secrets for the CI/CD pipeline. These secrets enable automated testing, Docker image building, and deployment to staging and production environments.

---

## Overview

The CI/CD pipeline requires **6 secrets** to be configured in your GitHub repository:

| Secret Name | Purpose | Required For |
|-------------|---------|--------------|
| `DOCKER_USERNAME` | Docker Hub authentication | Building and pushing images |
| `DOCKER_PASSWORD` | Docker Hub access token | Building and pushing images |
| `SSH_PRIVATE_KEY` | SSH authentication for deployments | Deploying to servers |
| `STAGING_HOST` | Staging server address | Staging deployments |
| `PRODUCTION_HOST` | Production server address | Production deployments |
| `SLACK_WEBHOOK` | Slack notifications | Build status notifications |

---

## How to Add Secrets to GitHub

### Step-by-Step Instructions

1. **Navigate to your GitHub repository**
   - Go to `https://github.com/YOUR_ORG/gen-scraper`

2. **Open Settings**
   - Click the **Settings** tab in the repository menu

3. **Access Secrets**
   - In the left sidebar, expand **Secrets and variables**
   - Click **Actions**

4. **Add a New Secret**
   - Click the **New repository secret** button
   - Enter the **Name** (exactly as shown below)
   - Paste the **Value** (see generation instructions for each secret)
   - Click **Add secret**

5. **Repeat for all 6 secrets**

---

## Secret Configurations

### 1. DOCKER_USERNAME

**Purpose**: Your Docker Hub username for authenticating to Docker Hub registry.

**How to Generate**:
- This is your Docker Hub account username
- If you don't have a Docker Hub account, create one at https://hub.docker.com/signup

**Example Value**:
```
mycompany
```

**Steps**:
1. Log in to Docker Hub at https://hub.docker.com
2. Your username is displayed in the top-right corner
3. Copy your username exactly as shown

---

### 2. DOCKER_PASSWORD

**Purpose**: Docker Hub access token for secure authentication (recommended over using your actual password).

**How to Generate**:
1. Log in to Docker Hub at https://hub.docker.com
2. Click your username in the top-right corner
3. Select **Account Settings**
4. Click **Security** in the left sidebar
5. Click **New Access Token**
6. Enter a description: `GitHub Actions CI/CD`
7. Set permissions: **Read, Write, Delete** (or **Read & Write** minimum)
8. Click **Generate**
9. **Copy the token immediately** (it won't be shown again)

**Example Value** (masked):
```
dckr_pat_1234567890abcdefghijklmnopqrstuvwxyz
```

**⚠️ Important**:
- Never commit this token to your repository
- Store it securely - you cannot retrieve it after closing the dialog
- If lost, generate a new token and update the GitHub secret

---

### 3. SSH_PRIVATE_KEY

**Purpose**: SSH private key for authenticating to staging and production servers during deployment.

**How to Generate**:

1. **Generate a new SSH key pair** (on your local machine or CI server):
   ```bash
   ssh-keygen -t ed25519 -C "github-actions@gen-scraper" -f ~/.ssh/github_actions_deploy
   ```
   
   - Press Enter when prompted for a passphrase (leave empty for CI/CD)
   - This creates two files:
     - `~/.ssh/github_actions_deploy` (private key - for GitHub Secret)
     - `~/.ssh/github_actions_deploy.pub` (public key - for servers)

2. **Copy the private key**:
   ```bash
   cat ~/.ssh/github_actions_deploy
   ```
   
   Copy the entire output, including:
   ```
   -----BEGIN OPENSSH PRIVATE KEY-----
   ...
   -----END OPENSSH PRIVATE KEY-----
   ```

3. **Add the public key to your servers**:
   ```bash
   # Copy public key
   cat ~/.ssh/github_actions_deploy.pub
   
   # On each server (staging and production), add to authorized_keys:
   ssh user@your-server
   echo "PUBLIC_KEY_CONTENT" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

**Example Value** (masked):
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBK1234567890abcdefghijklmnopqrstuvwxyzABCDEF==
-----END OPENSSH PRIVATE KEY-----
```

**⚠️ Important**:
- Keep the private key secure and never commit it to the repository
- Use a dedicated key pair for CI/CD (don't reuse personal keys)
- Ensure the public key is added to the `authorized_keys` file on both staging and production servers
- The key should have no passphrase for automated deployments

---

### 4. STAGING_HOST

**Purpose**: The hostname or IP address of your staging server where the application will be deployed for testing.

**How to Generate**:
- This is the address of your staging server
- Can be a hostname (e.g., `staging.example.com`) or IP address (e.g., `192.168.1.100`)

**Example Values**:
```
staging.gen-scraper.com
```
or
```
10.0.1.50
```

**Steps**:
1. Identify your staging server's hostname or IP address
2. Ensure the server is accessible via SSH from GitHub Actions runners
3. Verify SSH access works: `ssh user@staging.gen-scraper.com`

**⚠️ Important**:
- Ensure the server has the SSH public key added (see `SSH_PRIVATE_KEY` above)
- The server should have Docker and Docker Compose installed
- Firewall rules should allow SSH access (port 22) from GitHub Actions IP ranges

---

### 5. PRODUCTION_HOST

**Purpose**: The hostname or IP address of your production server where the application will be deployed after manual approval.

**How to Generate**:
- This is the address of your production server
- Can be a hostname (e.g., `app.example.com`) or IP address (e.g., `203.0.113.10`)

**Example Values**:
```
app.gen-scraper.com
```
or
```
203.0.113.10
```

**Steps**:
1. Identify your production server's hostname or IP address
2. Ensure the server is accessible via SSH from GitHub Actions runners
3. Verify SSH access works: `ssh user@app.gen-scraper.com`

**⚠️ Important**:
- Ensure the server has the SSH public key added (see `SSH_PRIVATE_KEY` above)
- The server should have Docker and Docker Compose installed
- Firewall rules should allow SSH access (port 22) from GitHub Actions IP ranges
- Production deployments require manual approval in the GitHub Actions workflow

---

### 6. SLACK_WEBHOOK

**Purpose**: Slack Incoming Webhook URL for sending build status notifications to your team's Slack channel.

**How to Generate**:

1. **Go to Slack Apps**:
   - Visit https://api.slack.com/apps
   - Click **Create New App**

2. **Create the App**:
   - Select **From scratch**
   - App Name: `Gen Scraper CI/CD`
   - Select your workspace
   - Click **Create App**

3. **Enable Incoming Webhooks**:
   - In the left sidebar, click **Incoming Webhooks**
   - Toggle **Activate Incoming Webhooks** to **On**

4. **Add Webhook to Workspace**:
   - Scroll down and click **Add New Webhook to Workspace**
   - Select the channel where notifications should be posted (e.g., `#deployments`)
   - Click **Allow**

5. **Copy the Webhook URL**:
   - The webhook URL will be displayed
   - Copy the entire URL (starts with `https://hooks.slack.com/services/`)

**Example Value** (masked):
```
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
```

**⚠️ Important**:
- Never commit this webhook URL to your repository
- Anyone with this URL can post messages to your Slack channel
- If compromised, revoke the webhook and generate a new one

**Optional**: If you don't want Slack notifications, you can skip this secret. The CI/CD pipeline will continue to work, but the Slack notification step will be skipped.

---

## Verification

After adding all secrets, verify they are configured correctly:

1. **Check Secrets List**:
   - Go to **Settings** → **Secrets and variables** → **Actions**
   - You should see all 6 secrets listed:
     - `DOCKER_USERNAME`
     - `DOCKER_PASSWORD`
     - `SSH_PRIVATE_KEY`
     - `STAGING_HOST`
     - `PRODUCTION_HOST`
     - `SLACK_WEBHOOK`

2. **Test the Pipeline**:
   - Push a commit to trigger the CI/CD workflow
   - Go to **Actions** tab in your repository
   - Watch the workflow run and verify each step completes successfully

3. **Common Issues**:
   - **Docker push fails**: Check `DOCKER_USERNAME` and `DOCKER_PASSWORD`
   - **Deployment fails**: Verify `SSH_PRIVATE_KEY` is correct and public key is on servers
   - **Cannot connect to server**: Check `STAGING_HOST` and `PRODUCTION_HOST` values
   - **No Slack notifications**: Verify `SLACK_WEBHOOK` URL is correct

---

## Security Best Practices

1. **Rotate Secrets Regularly**:
   - Update Docker access tokens every 6-12 months
   - Rotate SSH keys annually or when team members leave

2. **Limit Access**:
   - Only repository administrators should have access to secrets
   - Use separate keys for staging and production if possible

3. **Monitor Usage**:
   - Review GitHub Actions logs regularly
   - Check for unauthorized access attempts on your servers

4. **Backup**:
   - Store secrets securely in a password manager
   - Document the process for regenerating secrets if lost

5. **Audit**:
   - Periodically review which secrets are configured
   - Remove unused secrets
   - Verify secrets are still valid and working

---

## Troubleshooting

### Docker Authentication Fails

**Error**: `unauthorized: authentication required`

**Solution**:
1. Verify `DOCKER_USERNAME` is correct (case-sensitive)
2. Regenerate `DOCKER_PASSWORD` access token
3. Ensure the token has **Read & Write** permissions

### SSH Connection Fails

**Error**: `Permission denied (publickey)`

**Solution**:
1. Verify the SSH public key is in `~/.ssh/authorized_keys` on the server
2. Check file permissions: `chmod 600 ~/.ssh/authorized_keys`
3. Ensure `SSH_PRIVATE_KEY` includes the full key with headers and footers
4. Test SSH connection manually: `ssh -i ~/.ssh/github_actions_deploy user@server`

### Slack Notifications Not Received

**Error**: Workflow succeeds but no Slack message

**Solution**:
1. Verify `SLACK_WEBHOOK` URL is complete and correct
2. Check the Slack channel permissions
3. Test the webhook manually:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     YOUR_WEBHOOK_URL
   ```

---

## Additional Resources

- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Docker Hub Access Tokens](https://docs.docker.com/docker-hub/access-tokens/)
- [SSH Key Generation Guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)

---

## Support

If you encounter issues configuring secrets:

1. Check the [CI/CD Pipeline Documentation](ci_cd_pipeline.md)
2. Review GitHub Actions workflow logs for specific error messages
3. Contact the DevOps team for assistance

---

**Last Updated**: May 2, 2026  
**Maintained By**: DevOps Team
