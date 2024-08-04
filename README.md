# todo_api

simple todo RESTful api and client

Current status:
  app.py is working on a tests server
  task_cli handles add/delete/tree  - needs modify


  API:
  GET /tasks - get all tasks
  GET /tasks/search/<keyword> - search tasks
  GET /tasks/search/<field>/<keyword> - search for matches in a particular field
  GET /tasks/task_id/<task_id> - get a single task
  PUT /tasks/task_id/<task_id> - update a single task
  POST /tasks - create a task (task_id automatically assigned)
  DELETE /tasks/delete/<task_id> - delete a single task

  task structure JSON:
    - task_id: required added automatically
    - status: needs to be set to not_started if left out.
    - parent: optional, used to create tree structure
    - name: not enforced, but will break cli if missing
    - type:  not implemented yet, but here are some I have thought about
        - category: top level things (Today, Work, Home, Hobby1, Hobby2)
        - task: quick thing to do
        - project: bigger collection
        - subtask: subtask for task or project
        - note: info anout task or comment
        - pointer: place holder referencing a task in another tree.  Like Today may be mostly populated with pointers to tasks in other categories that need attention today
    - dates - not implemented yet
        - created: implement as an automatic
        - updated: implement as an automatic
        - started: automatic on status change?
        - due: set to COB today if missing?
        - completed: automatic on status change?
    - all other fields are accepted, I'm sure other fields will be standardized soon


 Todo:
   - Add template list and api
   - templates are repetitive tasks that will get created automaticall
     - daily
     - weekly
     - monthly
     - yearly
    - keep in seperate table, or as a record type in tasks
    - needs api (unless handled as record type)

    