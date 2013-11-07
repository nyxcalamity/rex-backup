rex-backup
----

Simple backup utility.

Requirements
----

- installed python 3.3+
- next permissions are required
    - read/write:dir where script is located
    - read/write:dir to which archive will be copied
    - read:dir to be backed up
- if any of those are shares they should be mounted


Quick guide:
---

Making use of rex-backup can be achieved in three steps:
1st) Copy scripts and resources folders to you preferred location (we will further assume that it's /home/user/rex-backup).
2nd) Edit config.xml to suit your needs (see the file for formatting rules).
3rd) Run the rex-backup.py script like next: python /home/user/rex-backup/scripts/rex_backup.py

The script will automatically pick up settings from config.xml. It will try to archive a configured source directory, copy
generated archive to the target folder. Then if configured it will check archive integrity (if files names and their mtimes
in archive match correspondingly files in the source dir), send reports via email and clean up tmp dirs. It can also perform
archive rotation by deleting archives which were made certain number of days ago.

Some tips:
---

Linux share mount example:
sudo mkdir -p /mnt/nas

manual:
sudo mount -t cifs //192.168.178.49/backup -o uid=1000,username=uname,dom=CRXMARKETS,password=pword /mnt/nas

fstab:
//192.168.178.49/backup /mnt/nas cifs uid=1000,username=uname,dom=CRXMARKETS,password=pword,iocharset=utf8,noperm 0 0