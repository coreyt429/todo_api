# todo_api

simple todo RESTful api and client

This project serves two purposes.

1) provide a todo list that works the way I work. This means it may not be good for you :)
2) a project to make me use flask and build an html/javascript front end

Current status:
  app.py is working on a tests server
  task_cli handles add/delete/tree  - needs modify


  API:
  # task - object describing a task or project
  GET /task - get all tasks
  GET /task/search/<keyword> - search tasks
  GET /task/search/<field>/<keyword> - search for matches in a particular field
  GET /task/<task_id> - get a single task
  PUT /task/<task_id> - update a single task
  POST /task - create a task (task_id automatically assigned)
  DELETE /task/<task_id> - delete a single task

  # template - object describing a template for creating repetitive tasks
  GET /template - get all templates
  GET /template/<template_id> - get a single template
  PUT /template/<template_id> - update a single template
  POST /template - create a template (template_id automatically assigned)
  DELETE /template/<template_id> - delete a single template


  task structure JSON:
    - task_id: required added automatically
    - status: needs to be set to not_started if left out.
    - parent: optional, used to create tree structure
    - name: not enforced, but will break cli if missing
    - type:  not implemented yet, but here are some I have thought about
        - category: top level things (Today, Work, Home, Hobby1, Hobby2)
          - deprecated categories are hard coded in the client now
        - context: scope of task (Work, Home, Hobby, etc)
        - task: quick thing to do
        - project: bigger collection
        - subtask: subtask for task or project
          - deprecated subtasks are now just tasks with a parent
        - note: info anout task or comment
        - pointer: place holder referencing a task in another tree.  Like Today may be mostly populated with pointers to tasks in other categories that need attention today
          - deprecated   categories like today, this week, this month, etc now just use logic to select tasks to display
    - timestamps - 
        - created: implement as an automatic
        - updated: implement as an automatic
        - started: automatic on status change?
          - not implemented, maybe not ever
        - due: set to COB today if missing?
        - completed: automatic on status change?
    - all other fields are accepted, I'm sure other fields will be standardized soon

 Todo:
  actual todo's are in my todo list now.

    