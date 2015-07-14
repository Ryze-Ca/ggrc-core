# Copyright (C) 2015 Google Inc., authors, and contributors <see AUTHORS file>
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
# Created By: miha@reciprocitylabs.com
# Maintained By: miha@reciprocitylabs.com


from sqlalchemy import and_

from ggrc import db
from ggrc.converters import errors
from ggrc.converters.handlers import UserColumnHandler
from ggrc.login import get_current_user
from ggrc.models import Person
from ggrc_basic_permissions.models import Role
from ggrc_basic_permissions.models import UserRole


class ProgramRoleColumnHandler(UserColumnHandler):

  role_id = -1

  def parse_item(self):
    users = set()
    email_lines = self.raw_value.splitlines()
    owner_emails = filter(unicode.strip, email_lines)  # noqa
    for raw_line in owner_emails:
      email = raw_line.strip().lower()
      person = self.get_person(email)
      if person:
        users.add(person)
      else:
        self.add_warning(errors.UNKNOWN_USER_WARNING, email=email)

    if not users:
      self.add_warning(errors.OWNER_MISSING)
      users.add(get_current_user())

    return list(users)

  def set_obj_attr(self):
    pass

  def get_value(self):
    user_role_ids = db.session.query(UserRole.person_id).filter_by(
        role_id=self.role_id,
        context_id=self.row_converter.obj.context_id)
    users = Person.query.filter(Person.id.in_(user_role_ids))
    emails = [user.email for user in users]
    return "\n".join(emails)

  def remove_current_roles(self):
    UserRole.query.filter_by(
        role_id=self.role_id,
        context_id=self.row_converter.obj.context_id).delete()

  def insert_object(self):
    if self.dry_run or not self.value:
      return
    self.remove_current_roles()
    for owner in self.value:
      user_role = UserRole(
          role_id=self.role_id,
          context_id=self.row_converter.obj.context_id,
          person_id=owner.id
      )
      db.session.add(user_role)
    self.dry_run = True


class ProgramOwnerColumnHandler(ProgramRoleColumnHandler):

  def __init__(self, row_converter, key, **options):
    self.role_id = Role.query.filter_by(name="ProgramOwner").one().id
    super(self.__class__, self).__init__(row_converter, key, **options)


class ProgramEditorColumnHandler(ProgramRoleColumnHandler):

  def __init__(self, row_converter, key, **options):
    self.role_id = Role.query.filter_by(name="ProgramEditor").one().id
    super(self.__class__, self).__init__(row_converter, key, **options)


class ProgramReaderColumnHandler(ProgramRoleColumnHandler):

  def __init__(self, row_converter, key, **options):
    self.role_id = Role.query.filter_by(name="ProgramReader").one().id
    super(self.__class__, self).__init__(row_converter, key, **options)


class UserRoleColumnHandler(UserColumnHandler):

  _role_map = {
    "admin": "ggrc admin"
  }

  _allowed_roles = [
      "Reader",
      "Editor",
      "gGRC Admin",
  ]

  def parse_item(self):
    value = self.raw_value.lower()
    name = self._role_map.get(value, value)
    return Role.query.filter_by(name=name).first()

  def set_obj_attr(self):
    pass

  def get_value(self):
    return ""

  def remove_current_roles(self):
    allowed_role_ids = db.session.query(Role.id).filter(
        Role.name.in_(self._allowed_roles))
    UserRole.query.filter(and_(
        UserRole.role_id.in_(allowed_role_ids),
        UserRole.person_id == self.row_converter.obj.id)
    ).delete(synchronize_session="fetch")

  def insert_object(self):
    if self.dry_run or not self.value:
      return
    self.remove_current_roles()
    user_role = UserRole(
        role_id=self.value.id,
        person_id=self.row_converter.obj.id
    )
    db.session.add(user_role)
    self.dry_run = True

COLUMN_HANDLERS = {
    "program_owner": ProgramOwnerColumnHandler,
    "program_editor": ProgramEditorColumnHandler,
    "program_reader": ProgramReaderColumnHandler,
    "user_role": UserRoleColumnHandler,
}
