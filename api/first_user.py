from sqlalchemy.orm import sessionmaker
from main import engine, User
import bcrypt

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

hashed_password = bcrypt.hashpw("password".encode("utf-8"), bcrypt.gensalt())
new_user = User(username="admin", hashed_password=hashed_password.decode("utf-8"))
db.add(new_user)
db.commit()
