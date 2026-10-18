with open('service.py', 'r') as f:
    content = f.read()

# Fix the indentation
content = content.replace(
    '''        try:
            payload = jwt.decode(token, self._settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_error

                    user = await self._users_repository.get_user(username)
                    if user is None:
                        raise credentials_error

                    return user
                except JWTError:
                    raise credentials_error''',
    '''        try:
            payload = jwt.decode(token, self._settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_error

            user = await self._users_repository.get_user(username)
            if user is None:
                raise credentials_error

            return user
        except JWTError:
            raise credentials_error'''
)

with open('service.py', 'w') as f:
    f.write(content)
print('Fixed')