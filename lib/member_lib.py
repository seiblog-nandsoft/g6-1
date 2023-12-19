from lib.common import is_none_datetime


def check_email_certify(config, member):
    """이메일 인증 사용시 체크"""
    if not config.cf_use_email_certify:
        return False

    if not is_none_datetime(member.mb_email_certify):
        return False

    return True


def member_check(config, member):
    if member.mb_intercept_date or member.mb_leave_date:  # 차단 되었거나, 탈퇴한 회원이면 세션 초기화
        return False

    if config.cf_use_email_certify and not check_email_certify(config, member):
        return False

    return True
