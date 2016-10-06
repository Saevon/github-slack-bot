WEB_PATH=/var/www/github-slack-bot

PROJECT=$(pwd)


# Setup the WSGI directory
mkdir ${WEB_PATH}
mkdir ${WEB_PATH}/logs
mkdir ${WEB_PATH}/data

ln -s ${PROJECT}/config.bash ${WEB_PATH}/
ln -s ${PROJECT}/wsgi.ini ${WEB_PATH}/

ln -s ${PROJECT}/wsgi.py ${WEB_PATH}/

cd ${WEB_PATH}
chgrp -h github-slack-bot wsgi.py
chmod g=r wsgi.py
chown github-slack-bot:github-slack-bot logs data
chmod g=rwX logs logs/main.log data
cd ${PROJECT}



# Setup nginx
ln -s ${PROJECT}/nginx.conf /etc/nginx/sites-available/github-slack-bot
ln -s /etc/nginx/sites-available/github-slack-bot /etc/nginx/sites-available/
ln -s ${PROJECT}/logrotate.conf /etc/logrotate.d/nginx.github-slack-bot

# Setup current folder
cd ${PROJECT}
ln -s run-wsgi.bash github-slack-bot

find . -name "*.py" -exec chgrp github-slack-bot {} \; -exec chmod g=r {} \;


# Now setup the init.d / upstart
echo "Now setup the init.d and start everything"
