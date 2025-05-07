# Blood Bank Management System

A comprehensive web-based solution for managing blood bank operations, facilitating efficient blood donation and distribution processes.

## 🚀 Features

### Admin Features
- 📊 Real-time dashboard with blood inventory statistics
- 👥 Manage donor and patient records
- ✅ Approve/reject blood donation requests
- ✅ Approve/reject blood requests
- 📈 Track blood stock levels across different blood groups
- 📋 View complete history of blood donations and requests
- 🔄 Update blood unit counts for specific blood groups

### Donor Features
- 👤 Easy account creation and management
- 🩸 Schedule blood donations
- 📊 View donation history with status tracking
- 🏥 Request blood when needed
- 📱 User-friendly dashboard with request statistics

### Patient Features
- 👤 Quick account registration
- 🏥 Request specific blood types
- 📊 Track request status (Pending/Approved/Rejected)
- 📱 Access to request history

## 🛠️ Tech Stack

- **Backend**: Django (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite
- **Authentication**: Django's built-in authentication system
- **Deployment**: Heroku (via Procfile)

## 📸 Screenshots

### Homepage
![homepage snap](https://github.com/PranayHaldiya/bloodbankmanagement/blob/main/static/screenshot/homepage.png?raw=true)

### Admin Dashboard
![dashboard snap](https://github.com/PranayHaldiya/bloodbankmanagement/blob/main/static/screenshot/admin%20dashboard.png?raw=true)

### Blood Donation 
![invoice snap](https://github.com/PranayHaldiya/bloodbankmanagement/blob/main/static/screenshot/blood%20donation.png?raw=true)

### Blood Request
![doctor snap](https://github.com/PranayHaldiya/bloodbankmanagement/blob/main/static/screenshot/blood%20request.png?raw=true)

## 🚀 Getting Started

### Prerequisites
- Python 3.x
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bloodbankmanagement.git
cd bloodbankmanagement
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up the database:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create a superuser (admin account):
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

6. Access the application at:
```
http://127.0.0.1:8000/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For support, please open an issue in the GitHub repository.

## 🙏 Acknowledgments

- Django Documentation
- All contributors who have helped in the development of this project
