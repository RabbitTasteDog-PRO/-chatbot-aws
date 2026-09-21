"""공용 DB에 저장할 일반 회원 정보를 Django 인증 규칙으로 검증한다."""
from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    """아이디와 비밀번호 두 번만 받아 해시된 비밀번호로 회원을 만든다."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = '아이디'
        self.fields['password1'].label = '비밀번호'
        self.fields['password2'].label = '비밀번호 확인'
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'
