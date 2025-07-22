#!/data/data/com.termux/files/usr/bin/bash
cd $HOME
tmux new-session -d -s mybot 'python bot.py'
