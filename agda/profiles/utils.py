import cracklib


def get_cracklib_complaints(password):
    """Sanity checking interface to cracklib.

    We expect a version of cracklib that returns the password unchanged and
    raises complaints as ValueError (as for example 2.8.16 does, and not as
    2.8.9, which returns None or complaints as strings).
    """
    good_password = "l0381903j++12+192A"
    try:
        if cracklib.FascistCheck(good_password) != good_password:
            return "cracklib interface is faulty (3)"  # Password not returned unchanged.
    except ValueError:
        return "cracklib interface is faulty (2)"  # Complaints on good password.
    except:
        return "cracklib interface is faulty (4)"  # Other interface error.

    def _fascist_check(pw):
        try:
            cracklib.FascistCheck(pw)
        except ValueError, e:
            return str(e)

    if _fascist_check("bad") != "it is WAY too short":
        # Should have complained about WAY too short password.
        return "cracklib interface is faulty (1)"
    if isinstance(password, unicode):
        password = password.encode("utf-8")
    return _fascist_check(password)
