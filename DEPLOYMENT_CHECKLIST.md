# IRONFORGE production launch checklist

- [ ] Create PostgreSQL database.
- [ ] Set `.env` secrets.
- [ ] Run `python manage.py makemigrations && python manage.py migrate`.
- [ ] Create Django superuser.
- [ ] Add initial plans and coaches in `/admin/`.
- [ ] Create Razorpay account and production keys.
- [ ] Configure Razorpay webhook URL.
- [ ] Set exact CORS origins.
- [ ] Deploy behind HTTPS.
- [ ] Configure backups and monitoring.
- [ ] Replace remaining V9 localStorage UI actions with IFAPI calls.
- [ ] Test registration/login/logout/refresh.
- [ ] Test coach request workflow.
- [ ] Test payment success/failure/refund flows.
- [ ] Never commit `.env`.
