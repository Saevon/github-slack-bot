# github-slack-bot
A bot that sends personal slack messages when a PR is assigned


## Install

To setup the bot as an init.d script you need the following files

 * `./env.py`: needs to be set up with the correct tokens an user mappings
 * `/etc/sysconfig/github-slack-bot': Config file which should contain the path to the exec CWD in `${BOT_CMD}`
 * `/etc/init.d/github-slack-bot`: The init.d file in this repo `github-slack-bot-init`

 Then run the following

 ```
sudo update-rc.d github-slack-bot defaults
 ```

## Updating

If you change the init.d script run `systemctl daemon-reload`


## Running

You can run the bot by `python bot.py`
You can also use the `github-slack-bot` script to run the file with logging

## Logs

If you ran the bot using the `github-slack-bot` script, then the log files are all in `/var/log/`

 * `github-slack-bot.log`: Merged log of stderr and stdout
 * `github-slack-bot.out.log`: stdout Log
 * `github-slack-bot.error.log`: stderr Log
