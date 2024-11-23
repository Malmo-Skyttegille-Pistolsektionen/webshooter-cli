from webshooter_client.common.webshooter_rc import WebShooterRC


def test_standard(resource_testfile_rootdir_w_path):
    wsrc = WebShooterRC.load_config(configfile=resource_testfile_rootdir_w_path("webshooter.rc"))

    assert wsrc is not None
    assert wsrc.unicode
