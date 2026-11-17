# Staff roles

The portal uses two access levels:

| Access level | Actions |
| --- | --- |
| Staff reviewer | Read submissions, add tags and comments, vote, preview and download individual files or submissions. |
| Submission Manager | All staff reviewer actions, plus delete submissions and download the complete ZIP or Excel export. |

`is_staff=True` gives staff reviewer access. The `Submission Managers` Django group gives the `delete_submission` and `export_all_submissions` permissions. The API checks these permissions. The dashboard hides the delete and full export buttons when a staff account does not have them.

Migration `0018_staff_manager_role` gives the manager group to every existing staff account. New staff accounts and accounts promoted to staff also receive it. This keeps current access for everyone. A Django superuser has all permissions even without the group.

To make a staff account reviewer-only, open Django admin as a superuser, edit the account, and remove `Submission Managers` from its groups. Keep `Staff status` enabled. The change takes effect on the next API request. The account can still review and vote. To restore manager access, add the group again.

Removing the group from an existing staff account stays in effect; later account saves do not grant it again.
