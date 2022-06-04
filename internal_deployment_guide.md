# Internal Deployment Guide
### Software you need
- A terminal (e.g. Command Prompt)
- A file transfer client (e.g. WinSCP)

## Update production Code
1. Transfer all updated files using file transfer client
   - Do not use `git` or `gh`, it will wipe `wykoj/config.json` and `wykoj/static/profile_pics`
2. Run `tmux a -t wykoj` to attach to tmux session
3. `Ctrl+C` to terminate hypercorn
4. Run `hypercorn -b 0.0.0.0:3000 "wykoj:create_app()"`
5. `Ctrl+B D` to detach from session

## AWS Migration
1. Update your local copy of `wykoj/config.json` and `wykoj/static/profile_pics`.
2. Terminate all resources on old AWS account, take snapshot of wykojdb in RDS
3. Create new AWS account
4. Share wykojdb snapshot from old account to new account
5. Restore wykojdb snapshot (db.t3.micro, Singapore region)
6. Create EC2 Ubuntu 20.04 instance (t2.micro, Singapore region)
   - Add 16 GB general purpose storage
   - Configure security group inbound rules
     - All traffic: My IP
     - HTTP & HTTPS & MYSQL/Aurora: Anywhere - IPv4
   - Associate it with an Elastic IP address
7. Create Route 53 hosted zone for owo.idv.hk
   - Go to domain name registrar and configure NS records
   - Add an A record: wykoj.owo.idv.hk -> IP address of EC2 instance

## 12 Easy Steps to Set Up WYKOJ Website Server (Ubuntu 20.04)
### 1. SSH into server
```bash
ssh -i "path\to\wykoj.pem" ubuntu@[IP address of EC2 instance]
```

### 2. Update packages
```bash
sudo apt update
sudo apt -y upgrade
sudo reboot
```

### 3. Configure timezone
```bash
sudo timedatectl set-timezone Asia/Hong_Kong
```


### 4. Configure firewall
```bash
sudo apt install -y nginx
sudo ufw allow 'OpenSSH'
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 5. Install Python 3.9
```bash
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev python3-pip python3.9 python3.9-dev
```

### 6. Set aliases and environmental variables
```bash
sudo nano .bash_aliases
```

```bash
# File: ~/.bash_aliases
alias python='python3.9'
alias pip='python3.9 -m pip'
export PYTHONPYCACHEPREFIX=/tmp
export GCM_CREDENTIAL_STORE=cache
```

```bash
. .bash_aliases
```

### 7. Generate GitHub personal access token (PAT)
Expiration: No expiration <br>
Scopes: `repo` and `read:org`

### 8. Install GitHub CLI
```bash
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

### 9. Install wykoj
```bash
gh auth login  # GitHub.com > HTTPS > Yes > Paste PAT
gh repo clone wykstemteam/wykoj
cd wykoj
git submodule init
git submodule update
git submodule foreach git pull origin master
pip install -Ur requirements.txt
sudo ln -s ~/wykoj/502.html /var/www/html
```

Transfer your local copy of `wykoj/config.json` and `wykoj/static` to the server manually.

### 10. Run wykoj on tmux session
```bash
tmux new -s wykoj
hypercorn -b 0.0.0.0:3000 "wykoj:create_app()"
```

`Ctrl+B D` to detach from session.

### 11. Configure nginx
```bash
cd /etc/nginx
sudo nano nginx.conf
```

```bash
# File: /etc/nginx/nginx.conf
server_names_hash_bucket_size 64;  # Uncomment
```

```bash
sudo nano sites-available/wykoj.owo.idv.hk
```

```bash
# File: /etc/nginx/sites-available/wykoj.owo.idv.hk
server {
    listen 80;
    server_name wykoj.owo.idv.hk;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_intercept_errors on;

        error_page 502 /502.html;
    }

    location /502.html {
        root /var/www/html;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/wykoj.owo.idv.hk /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 12. Enable HTTPS with certbot
```bash
sudo snap install core
sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx
```
