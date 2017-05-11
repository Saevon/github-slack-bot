# github-slack-bot
A bot that sends personal slack messages when a PR is assigned


## Install

You can use the helper `setup.bash` to do most of the setup

To setup the bot as an init.d script you need the following files

 * `./env.py`: needs to be set up with the correct tokens an user mappings
 * `/etc/init.d/github-slack-bot`: The init.d file in this repo `github-slack-bot-init`
 * `./github-slack-bot`: link to the `run-python.bash`
 * `/var/www/github-slack-bot/config.bash`: should set any ENV_VARIABLES, specifically `${BOT_CWD}`

Then run the following

```
sudo update-rc.d github-slack-bot defaults
```

Remember! you also need to setup all the `.env` variables. You also need to get github to send webhook events to the new IP/URI

## Updating

If you change the init.d script run `systemctl daemon-reload`

If you just updated the code run
`service github-slack-bot restart`

If you change the server anme, nginx needs to know about it (IP counts). Add the new name under `server_name`

Then restart nginx

`service nginx restart`


## Nginx with uWSGI

install uwsgi

`apt-get install libpcre3 libpcre3-dev`
`pip install uwsgi`

Create links or move the following files

 * `/etc/nginx/sites-available/github-slack-bot`: Nginx File `nginx.conf`
 * `/etc/nginx/sites-enabled/github-slack-bot`: Should point to the `sites-available` file
 * `/var/www/github-slack-bot/wsgi.ini`
 * `/var/www/github-slack-bot/wsgi.py`

Setup the wsgi init.d (similar to the Install above)

 * `./github-slack-bot`: link to the `run-wsgi.bash`

Update the servername in the `nginx.conf`

Create the log folder

 * `/var/www/github-slack-bot/logs/`

Create the User

`useradd --system github-slack-bot`
`gpasswd -a "github-slack-bot" www-data`


### Running

You can run the bot by `python bot.py`
You can also use the `github-slack-bot` script to run the file with logging

## Logs

If you ran the bot using the `github-slack-bot` script, then the log files are all in `/var/www/github-slack-bot/logs/`

 * `main.log`: Merged log of stderr and stdout
 * `wsgi.log`: WSGI runner logs
 * `dev.log`: werkzeug runner logs
 * `nginx.access.log` Nginx access Logs
 * `nginx.error.log` Nginx Logs
