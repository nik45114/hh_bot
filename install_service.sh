#!/bin/bash

echo "🔧 Установка systemd service для HH Bot"
echo "========================================"

# Получаем текущего пользователя и путь
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

echo "Пользователь: $CURRENT_USER"
echo "Директория: $CURRENT_DIR"

# Создаем временный service файл с правильными путями
cat > /tmp/hh_bot.service << EOF
[Unit]
Description=HH Job Bot - Telegram bot for job applications automation
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$CURRENT_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10

StandardOutput=append:$CURRENT_DIR/bot.log
StandardError=append:$CURRENT_DIR/bot.log

[Install]
WantedBy=multi-user.target
EOF

# Копируем service файл
echo "📋 Копирование service файла..."
sudo cp /tmp/hh_bot.service /etc/systemd/system/hh_bot.service

# Перезагружаем systemd
echo "🔄 Перезагрузка systemd..."
sudo systemctl daemon-reload

# Включаем автозапуск
echo "✅ Включение автозапуска..."
sudo systemctl enable hh_bot.service

# Запускаем service
echo "🚀 Запуск сервиса..."
sudo systemctl start hh_bot.service

# Показываем статус
echo ""
echo "📊 Статус сервиса:"
sudo systemctl status hh_bot.service

echo ""
echo "✅ Установка завершена!"
echo ""
echo "Полезные команды:"
echo "  sudo systemctl status hh_bot    # Проверить статус"
echo "  sudo systemctl stop hh_bot      # Остановить"
echo "  sudo systemctl start hh_bot     # Запустить"
echo "  sudo systemctl restart hh_bot   # Перезапустить"
echo "  sudo journalctl -u hh_bot -f    # Логи"
echo "  tail -f $CURRENT_DIR/bot.log    # Логи файл"
