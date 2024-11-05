# Question: How to organise Models best?

Should models defined within the routes py-files, or parallel in a similar folder structure?
Or one file with all?

# ToDo: Create factory / constructor class methods for Models:

**Example:**

```
class UserPRM(BasePRM):
    something: str
    something_else: str

    @classmethod
    create_prm_with_user(cls, user: ABCUser):
        cls(something = user.get_username(),
            something_else = user.get_email())
``
