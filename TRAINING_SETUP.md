# GitHub Actions Setup Guide

## Required Configuration

### Step 1: Add GitHub Secrets

Go to your repository settings to add secrets for GitHub Actions notifications.

#### Discord Webhook (Optional but Recommended)

1. Go to your Discord server → Server Settings → Integrations → Webhooks
2. Click "New Webhook"
3. Name it "FixtureCast Training Bot"
4. Copy the Webhook URL
5. Go to GitHub repo → Settings → Secrets and variables → Actions
6. Click "New repository secret"
7. Name: `DISCORD_WEBHOOK_URL`
8. Value: Paste the Discord webhook URL
9. Click "Add secret"

#### Railway Token (Optional)

Only needed if Railway doesn't auto-watch your branch.

1. Go to Railway dashboard → Account → Tokens
2. Create new token with "Deployments" permissions
3. Copy the token
4. Go to GitHub repo → Settings → Secrets and variables → Actions
5. Click "New repository secret"
6. Name: `RAILWAY_TOKEN`
7. Value: Paste the Railway token
8. Click "Add secret"

### Step 2: Verify Workflow File

The workflow file `.github/workflows/train-models.yml` is already created and includes:

- ✅ Schedule trigger (Mondays 3 AM UTC)
- ✅ Manual trigger support
- ✅ Python 3.12 setup
- ✅ Dependency installation
- ✅ Model training
- ✅ Git commit and push
- ✅ Discord failure notifications
- ✅ Railway deployment trigger

### Step 3: Test the Workflow

**Manual Test:**

1. Go to GitHub repo → Actions tab
2. Select "Automated Weekly Training" from left sidebar
3. Click "Run workflow"
4. Select branch (main)
5. Click "Run workflow"

**Monitor Run:**

1. Watch the workflow execute in real-time
2. Check logs for any errors
3. Verify models were trained successfully
4. Confirm git commit was made (if models changed)

## Customization

### Change Training Schedule

Edit `.github/workflows/train-models.yml`:

```yaml
on:
  schedule:
    - cron: "0 3 * * 1"  # Change this line
```

Cron format: `minute hour day month day-of-week`

**Common schedules:**
- `0 3 * * 1` - Monday 3 AM UTC
- `0 2 * * 0` - Sunday 2 AM UTC
- `0 */12 * * *` - Every 12 hours
- `30 1 * * *` - Every day 1:30 AM UTC

### Modify Training Parameters

Edit `.github/workflows/train-models.yml` training step:

```yaml
- name: Train models
  run: |
    cd ml_engine
    python continuous_training.py --no-collect --train
```

Options:
- `--no-collect` - Skip data collection (faster)
- `--collect-only` - Only collect data, don't train
- `--no-train` - Skip training
- Remove flags to collect fresh data before training

## Troubleshooting

### Workflow Not Running

**Problem**: Schedule not triggering
- GitHub Actions sometimes delays scheduled tasks
- Can take up to 1 hour for first run
- Test with manual trigger first

**Solution**:
1. Verify workflow file is in main branch
2. Check GitHub Actions is enabled in Settings
3. Use manual trigger to test

### Models Not Committing

**Problem**: Training runs but no commit
- Models didn't change (expected behavior)
- Git configuration error
- File permissions issue

**Solutions**:
1. Check workflow logs for commit output
2. Verify git user is configured as "FixtureCast Training Bot"
3. Check if models directory has write permissions

### Discord Notification Not Sent

**Problem**: Training fails but no Discord message
- Webhook URL not set or invalid
- Network connectivity issue
- Webhook deleted

**Solutions**:
1. Verify `DISCORD_WEBHOOK_URL` secret is set
2. Test webhook manually with curl
3. Check Discord channel for webhook permissions

### Training Timeout

**Problem**: Training runs longer than 120 minutes
- Models too large
- Training data too big
- Slow CPU

**Solutions**:
1. Increase timeout in workflow (edit: `timeout-minutes`)
2. Reduce training data size
3. Use `--no-collect` flag to skip data collection

### Permission Denied Errors

**Problem**: Can't write to directories or files
- Repository permissions issue
- File ownership problem

**Solutions**:
1. Check GitHub Actions permissions in Settings → Actions
2. Ensure workflows can write to directories
3. Check file permissions locally and fix

## Verification Checklist

- [ ] Workflow file `.github/workflows/train-models.yml` exists
- [ ] GitHub Actions is enabled in repository settings
- [ ] (Optional) Discord webhook URL added to secrets
- [ ] (Optional) Railway token added to secrets
- [ ] Manual workflow trigger test successful
- [ ] Models trained and committed successfully
- [ ] New models deployed to Railway
- [ ] Metrics dashboard shows updated data

## Next Steps

1. ✅ Configure secrets (optional but recommended)
2. ✅ Run first manual training test
3. ✅ Verify models were trained and committed
4. ✅ Confirm deployment to Railway
5. ✅ Monitor scheduled runs going forward

## Support

For issues:
1. Check workflow logs in GitHub Actions tab
2. Review the error output carefully
3. Check system resources (disk space, memory)
4. Verify all dependencies are installed

## Security Notes

- Never commit API keys or tokens to git
- Use GitHub Secrets for sensitive data
- Rotate webhook URLs periodically
- Review workflow permissions regularly
- Monitor failed runs for security issues
