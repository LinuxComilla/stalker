# -*- coding: utf-8 -*-
# Copyright (c) 2009-2012, Erkan Ozgur Yilmaz
# 
# This module is part of Stalker and is released under the BSD 2
# License: http://www.opensource.org/licenses/BSD-2-Clause

import datetime
from sqlalchemy.ext.declarative import declared_attr
import warnings
from sqlalchemy import Table, Column, Integer, ForeignKey, Boolean, Interval
from sqlalchemy.orm import relationship, validates, synonym, reconstructor, backref
from stalker import User
from stalker.conf import defaults
from stalker.db import DBSession
from stalker.db.declarative import Base
from stalker.exceptions import OverBookedWarning, CircularDependencyError
from stalker.models.entity import Entity
from stalker.models.mixins import ScheduleMixin, StatusMixin

from stalker.log import logging_level
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging_level)

class Booking(Entity, ScheduleMixin):
    """Holds information about the time spend on a specific
    :class:`~stalker.models.task.Task` by a specific
    :class:`~stalker.models.auth.User`.
    
    Bookings are created per resource. It means, you need to record all the 
    works separately for each resource. So there is only one resource in a 
    Booking instance, thus :attr:`~stalker.models.task.Booking.duration`
    attribute is equal to the meaning of ``effort``.
    
    A :class:`~stalker.models.task.Booking` instance needs to be initialized
    with a :class:`~stalker.models.task.Task` and a
    :class:`~stalker.models.auth.User` instances.
    
    Adding overlapping booking for a :class:`~stalker.models.auth.User` will
    raise a :class:`~stalker.errors.OverBookedWarning`.
    
    :param task: The :class:`~stalker.models.task.Task` instance that this
      booking belongs to.
    
    :param resource: The :class:`~stalker.models.auth.User` instance that this
      booking is created for.
    """
    __auto_name__ = True
    __tablename__ = "Bookings"
    __mapper_args__ = {"polymorphic_identity": "Booking"}
    booking_id = Column("id", Integer, ForeignKey("Entities.id"),
                        primary_key=True)
    task_id = Column(Integer, ForeignKey("Tasks.id"), nullable=False)
    task = relationship(
        "Task",
        primaryjoin="Bookings.c.task_id==Tasks.c.id",
        uselist=False,
        back_populates="bookings",
        doc="""The :class:`~stalker.models.task.Task` instance that this 
        booking is created for"""
    )
    
    resource_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    resource = relationship(
        "User",
        primaryjoin="Bookings.c.resource_id==Users.c.id",
        uselist=False,
        back_populates="bookings",
        doc="""The :class:`~stalker.models.auth.User` instance that this 
        booking is created for"""
    )
    
    def __init__(
            self,
            task=None,
            resource=None,
            start=None,
            end=None,
            duration=None,
            **kwargs):
        super(Booking, self).__init__(**kwargs)
        kwargs['start'] = start
        kwargs['end'] = end
        kwargs['duration'] = duration
        ScheduleMixin.__init__(self, **kwargs)
        self.task = task
        self.resource = resource
    
    @validates("task")
    def _validate_task(self, key, task):
        """validates the given task value
        """
        if not isinstance(task, Task):
            raise TypeError("%s.task should be an instance of "
                            "stalker.models.task.Task not %s" %
                            (self.__class__.__name__,
                             task.__class__.__name__))
        
        return task
    
    @validates("resource")
    def _validate_resource(self, key, resource):
        """validates the given resource value
        """
        
        if resource is None:
            raise TypeError("%s.resource can not be None" %
                            self.__class__.__name__)

        if not isinstance(resource, User):
            raise TypeError("%s.resource should be a "
                            "stalker.models.auth.User instance not %s" %
                            (self.__class__.__name__,
                             resource.__class__.__name__))
        
        # check for overbooking
        for booking in resource.bookings:
            logger.debug('booking.start: %s' % booking.start)
            logger.debug('self.start: %s' % self.start)
            
            if booking.start == self.start or\
               booking.end == self.end or \
               (self.end > booking.start and
                self.end < booking.end) or \
               (self.start > booking.start and
                self.start < booking.end):
                warnings.warn(
                    "The resource %s is overly booked with %s and %s" %
                    (resource, self, booking),
                    OverBookedWarning
                )
        return resource


class Task(Entity, StatusMixin, ScheduleMixin):
    """Manages Task related data.
    
    Tasks are the smallest meaningful part that should be accomplished to
    complete a :class:`~stalker.models.project.Project`.
    
    .. versionadded: 0.2.0: Parent-child relation in Tasks
      
      Tasks can now have child Tasks. So you can create complex relations of
      Tasks to comply with your project needs.
    
    A Task needs to be created with a Project instance. It is also valid if no
    project is supplied but there is a parent Task passed to the parent
    argument. It is also possible to pass both project and the task.
    
    Because it will create an ambiguity, Stalker will raise a RuntimeWarning,
    if both project and task are given and the owner project of the given task
    is different then the supplied project instance. But again Stalker will
    warn the user but will continue to use the task as the parent and will
    correctly use the project of the given task as the project of the newly
    created task.
    
    The following codes are a couple of examples for creating Task instances::
      
      # with a project instance
      task1 = Task(name='Schedule', project=proj1)
      
      # with a parent task
      task2 = Task(name='Documentation', parent=task1)
      
      # or both
      task3 = Task(name='Test', project=proj1, parent=task1)
      
      # this will create a RuntimeWarning
      task4 = Task(name='Test', project=proj2, parent=task1) # task1 is not a
                                                             # task of proj2
      assert task4.project == proj1 # Stalker uses the task1.project for task4
      
      # this will also create a RuntimeError
      task3 = Task(name='Failure 2') # no project no parent, this is an orphan
                                     # task.
    
    The end of a task is calculated by using the duration of the Task itself
    and the working hours settings of the related Project instance. So the
    holidays or the vacations of the resources are taken in to account.
    
    A Tasks is called a ``container task`` if it has at least one child Task.
    And it is called a ``leaf task`` if it doesn't have any children Tasks. The
    resources in a container task is meaningless, cause the resources are
    defined by the child tasks.
    
    The :attr:`~stalker.core.models.task.Task.start` and
    :attr:`~stalker.core.models.task.Task.end` values for a container task
    is gathered from the child tasks. The start is equal to the earliest
    start value of the children tasks, and the end is equal to the
    latest end value of the children tasks.
    
    Stalker will check if there will be a cycle if one wants to parent a Task
    to a child Task of its own.
    
    The Task class itself is mixed with
    :class:`~stalker.models.mixins.StatusMixin` and
    :class:`~stalker.models.mixins.ScheduleMixin`. To be able to give the
    :class:`~stalker.models.task.Task` a *Status* and a *start* and *end* time.
    
    With every release of Stalker, the Stalker Tasks will try to be more
    compliant with TaskJuggler Tasks.
    
    :param parent: The parent Task or Project of this Task. Every Task in
      Stalker should be related with a :class:`~stalker.models.project.Project`
      instance. So if no parent task is desired, at least a Project instance
      should be passed as the parent of the created Task or the Task will be an
      orphan task and Stalker will raise a RuntimeError.
    
    :param int priority: It is a number between 0 to 1000 which defines the
      priority of the :class:`~stalker.models.task.Task`. The higher the value
      the higher its priority. The default value is 500.
    
    :param resources: The :class:`~stalker.models.auth.User`\ s assigned to
      this :class:`~stalker.models.task.Task`. A
      :class:`~stalker.models.task.Task` without any resource can not be
      scheduled.
    
    :type resources: list of :class:`~stalker.User`
    
    :param effort: The total effort that needs to be spend to complete this
      :class:`~stalker.models.task.Task`. Can be used to create an initial bid
      of how long this task will take. The effort is equally divided to the
      assigned resources. So if the effort is 10 days and 2
      :attr:`~stalker.models.task.Task.resources` is assigned then the
      :attr:`~stalker.models.task.Task.duration` of the task is going to be 5
      days (if both of the resources are free to work). The default value is
      stalker.conf.defaults.DEFAULT_TASK_DURATION.
      
      The effort argument defines the
      :attr:`~stalker.models.task.Task.duration` of the task. Every resource is
      counted equally effective and the
      :attr:`~stalker.models.task.Task.duration` will be calculated by the
      simple formula:
      
      .. math::
         
         {duration} = \\frac{{effort}}{n_{resources}}
      
      And changing the :attr:`~stalker.models.task.Task.duration` will also
      effect the :attr:`~stalker.models.task.Task.effort` spend. The
      :attr:`~stalker.models.task.Task.effort` will be calculated with the
      formula:
      
      .. math::
         
         {effort} = {duration} \\times {n_{resources}}
    
    :type effort: datetime.timedelta
    
    :param depends: A list of :class:`~stalker.models.task.Task`\ s that this
      :class:`~stalker.models.task.Task` is depending on. A Task can not depend
      to itself or any other Task which are already depending to this one in
      anyway or a CircularDependency error will be raised.
    
    :type depends: list of :class:`~stalker.models.task.Task`
    
    :param bool milestone: A bool (True or False) value showing if this task is
      a milestone which doesn't need any resource and effort.
    """
    #.. :param depends: A list of
    #:class:`~stalker.models.task.TaskDependencyRelation` objects. Holds
    #information about the list of other :class:`~stalker.models.task.Task`\ s
    #which the current one is dependent on.

    #.. giving information about the dependent tasks. The given list is iterated
    #and the :attr:`~stalker.models.task.Task.start` attribute is set to
    #the latest found :attr:`~stalker.models.task.Task.end` attribute of
    #the dependent :class:`~stalker.models.task.Task`\ s.

    #.. :type depends: list of :class:`~stalker.models.task.TaskDependencyRelation`


    #:param parent_task: Another :class:`~stalker.models.task.Task` which is the
    #parent of the current :class:`~stalker.models.task.Task`.

    #:class:`~stalker.models.task.Task`\ s can be grouped by using parent and
    #child relation.

    #:type parent_task: :class:`~stalker.models.task.Task`

    #:param sub_tasks: A list of other :class:`~stalker.models.task.Task`\ s
    #which are the child of the current one. A
    #:class:`~stalker.models.task.Task` with other child
    #:class:`~stalker.models.task.Task`\ s:

    #* can not have any resources
    #* can not have any effort set
    #* can not have any versions

    #The only reason of a :class:`~stalker.models.task.Task` to have other
    #:class:`~stalker.models.task.Task`\ s as child is to group them. So it
    #is meaningles to let a parent :class:`~stalker.models.task.Task` to have
    #any resource or any effort or any verions. The
    #:attr:`~stalker.models.task.Task.start`,
    #:attr:`~stalker.models.task.Task.end` and
    #:attr:`~stalker.models.task.Task.duration` attributes of a
    #:class:`~stalker.models.task.Task` with child classes will be based on
    #it childrens date attributes.

    #:type child_tasks: :class:`~stalker.models.task.Task`.

    #:param versions: A list of :class:`~stalker.models.version.Version` objects
    #showing the produced work on the repository. This is the relation between
    #database and the repository.

    #:type versions: list of :class:`~stalker.models.version.Version`
    #"""

    __auto_name__ = False
    __tablename__ = "Tasks"
    __mapper_args__ = {'polymorphic_identity': "Task"}
    task_id = Column("id", Integer, ForeignKey('Entities.id'),
                     primary_key=True)
    
    project_id = Column('project_id', Integer, ForeignKey('Projects.id'),
                        nullable=False)
    _project = relationship(
        'Project',
        primaryjoin='Tasks.c.project_id==Projects.c.id',
        back_populates='tasks',
        uselist=False,
    )
    
    parent_id = Column('parent_id', Integer, ForeignKey('Tasks.id'))
    parent = relationship(
        'Task',
        remote_side=[task_id],
        primaryjoin='Tasks.c.parent_id==Tasks.c.id',
        back_populates='children'
    )
    
    children = relationship(
      'Task',
       primaryjoin='Tasks.c.parent_id==Tasks.c.id',
        back_populates='parent',
       # single_parent=True
    )
    
    tasks = synonym('children')
    
    is_milestone = Column(
        Boolean,
        doc="""Specifies if this Task is a milestone.
        
        Milestones doesn't need any duration, any effort and any resources. It
        is used to create meaningful dependencies between the critical stages
        of the project.
        """
    )
    
    # UPDATE THIS: is_complete should look to Task.status, but it is may be
    # faster to query in this way, judge later
    is_complete = Column(
        Boolean,
        doc="""A bool value showing if this task is completed or not.
        
        There is a good article_ about why not to use an attribute called
        ``percent_complete`` to measure how much the task is completed.
        
        .. _article: http://www.pmhut.com/how-percent-complete-is-that-task-again
        """
    )
    
    depends = relationship(
        "Task",
        secondary="Task_Dependencies",
        primaryjoin="Tasks.c.id==Task_Dependencies.c.task_id",
        secondaryjoin="Task_Dependencies.c.depends_to_task_id==Tasks.c.id",
        backref="dependent_of",
        doc="""A list of :class:`~stalker.models.task.Task`\ s that this one is depending on.
        
        A CircularDependencyError will be raised when the task dependency
        creates a circular dependency which means it is not allowed to create
        a dependency for this Task which is depending on another one which in
        some way depends to this one again.
        """
    )
    
    resources = relationship(
        "User",
        secondary="Task_Resources",
        primaryjoin="Tasks.c.id==Task_Resources.c.task_id",
        secondaryjoin="Task_Resources.c.resource_id==Users.c.id",
        #backref="tasks",
        back_populates="tasks",
        doc="""The list of :class:`stalker.models.auth.User`\ s instances assigned to this Task.
        """
    )
    
    _effort = Column(Interval)
    priority = Column(Integer)
    
    bookings = relationship(
        "Booking",
        primaryjoin="Bookings.c.task_id==Tasks.c.id",
        back_populates="task",
        doc="""A list of :class:`~stalker.models.task.Booking` instances showing who and when spent how much effort on this task.
        """
    )

    versions = relationship(
        "Version",
        primaryjoin="Versions.c.version_of_id==Tasks.c.id",
        back_populates="version_of",
        doc="""A list of :class:`~stalker.models.version.Version` instances showing the files created for this task.
        """
    )

    def __init__(self,
                 project=None,
                 parent=None,
                 depends=None,
                 start=None,
                 end=None,
                 duration=None,
                 effort=None,
                 resources=None,
                 is_milestone=False,
                 priority=defaults.TASK_PRIORITY,
                 **kwargs):
        # update kwargs with extras
        kwargs['start'] = start
        kwargs['end'] = end
        kwargs['duration'] = duration
        
        logger.debug('Task kwargs      : %s' % kwargs)
        logger.debug('Task project arg : %s' % project)
        logger.debug('Task parent arg  : %s' % parent)
        super(Task, self).__init__(**kwargs)
        
        # call the mixin __init__ methods
        StatusMixin.__init__(self, **kwargs)
        ScheduleMixin.__init__(self, **kwargs)
        
        logger.debug('Task kwargs (after super inits) : %s' % kwargs)
        logger.debug('Task project arg (after inits)  : %s' % project)
        logger.debug('Task parent arg (after inits)   : %s' % parent)
        
        self.parent = parent
        self._project =  project
        
        self.bookings = []
        self.versions = []
        
        self.is_milestone = is_milestone
        self.is_complete = False

        if depends is None:
            depends = []

        self.depends = depends

        if self.is_milestone:
            resources = None

        if resources is None:
            resources = []

        self.resources = resources
        self._effort = None
        self.effort = effort
        
        self.priority = priority

    @reconstructor
    def __init_on_load__(self):
        """initialized the instance variables when the instance created with
        SQLAlchemy
        """
        # UPDATE THIS
        self.bookings = []
        self.versions = []

        # call supers __init_on_load__
        super(Task, self).__init_on_load__()

    def __eq__(self, other):
        """the equality operator
        """
        return super(Task, self).__eq__(other) and isinstance(other, Task)

    @validates("bookings")
    def _validate_bookings(self, key, booking):
        """validates the given bookings value
        """
        if not isinstance(booking, Booking):
            raise TypeError(
                "all the elements in the %s.bookings should be an instances "
                "of stalker.models.task.Booking not %s instance" %
                (self.__class__.__name__, booking.__class__.__name__))
        
        return booking

    @validates("is_complete")
    def _validate_is_complete(self, key, complete_in):
        """validates the given complete value
        """
        return bool(complete_in)

    @validates("depends")
    def _validate_depends(self, key, depends):
        """validates the given depends value
        """
        if not isinstance(depends, Task):
            raise TypeError("all the elements in the depends should be an "
                            "instance of stalker.models.task.Task")
        
        # check for the circular dependency
        _check_circular_dependency(depends, self, 'depends')
        
        return depends

    def _validate_effort(self, effort):
        """validates the given effort
        """
        
        if not isinstance(effort, datetime.timedelta):
            effort = None
        
        if effort is None:
            # take it from the duration and resources
            
            num_of_resources = len(self.resources)
            if num_of_resources == 0:
                num_of_resources = 1
            
            effort = self.duration * num_of_resources
        
        return effort

    def _effort_getter(self):
        """the getter for the effort property
        """
        return self._effort

    def _effort_setter(self, effort_in):
        """the setter for the effort property
        """
        self._effort = self._validate_effort(effort_in)
        
        # update the duration
        num_of_resources = len(self.resources)
        if num_of_resources == 0:
            num_of_resources = 1
        
        self.duration = self._effort / num_of_resources

    effort = synonym(
        "_effort",
        descriptor=property(
            fget=_effort_getter,
            fset=_effort_setter
        ),
        doc="""The total effort that needs to be spend to complete this Task.
        
        Can be used to create an initial bid of how long this task going to
        take. The effort is equally divided to the assigned resources. So if
        the effort is 10 days and 2 resources is assigned then the
        :attr:`~stalker.models.task.Task.duration` of the task is going to be 5
        days (if both of the resources are free to work). The default value is
        stalker.conf.defaults.DEFAULT_TASK_DURATION.
      
        The effort defines the :attr:`~stalker.models.task.Task.duration` of
        the task. Every resource is counted equally effective and the
        :attr:`~stalker.models.task.Task.duration` will be calculated by the
        simple formula:
        
        .. math::
           
           {duration} = \\frac{{effort}}{n_{resources}}
        
        And changing the :attr:`~stalker.models.task.Task.duration` will also
        effect the :attr:`~stalker.models.task.Task.effort` spend. The
        :attr:`~stalker.models.task.Task.effort` will be calculated with the
        formula:
           
        .. math::
           
           {effort} = {duration} \\times {n_{resources}}
        """
    )

    @validates("is_milestone")
    def _validate_is_milestone(self, key, is_milestone):
        """validates the given milestone value
        """
        if is_milestone:
            self.resources = []
        
        return bool(is_milestone)
    
    @validates('parent')
    def _validate_parent(self, key, parent):
        """validates the given parent value
        """
        if parent is not None:
            # if it is not a Task instance, go mad (cildir!!)
            if not isinstance(parent, Task):
                raise TypeError('%s.parent should be an instance of '
                                'stalker.models.task.Task, not '
                                'a %s' %  (self.__class__.__name__,
                                           parent.__class__.__name__))
        
            # check for cycle
            _check_circular_dependency(self, parent, 'children')
        
        return parent
    
    @validates('_project')
    def _validates_project(self, key, project):
        """validates the given project instance
        """
        if project is None:
            # check if there is a parent defined
            if self.parent:
                # use its project as the project
                
                # disable autoflush
                # to prevent prematurely flush the parent
                autoflush = DBSession.autoflush
                DBSession.autoflush = False
                
                project = self.parent.project
                
                # reset autoflush
                DBSession.autoflush = autoflush
            else:
                # no project, no task, go mad again!!!
                raise TypeError('%s.project should be an instance of '
                                'stalker.models.project.Project, not %s. Or '
                                'please supply a stalker.models.task.Task '
                                'in the parent, so Stalker can use the '
                                'project of the supplied parent task' %
                                (self.__class__.__name__,
                                 project.__class__.__name__))
        
        from stalker import Project
        if not isinstance(project, Project):
            # go mad again it is not a project instance
            raise TypeError('%s.project should be an instance of '
                            'stalker.models.project.Project, not %s' % 
                            (self.__class__.__name__,
                             project.__class__.__name__))
        else:
            # check if there is a parent
            if self.parent:
                # check if given project is matching the parent.project
                if self.parent._project != project:
                    # don't go mad again, but warn the user that there is an
                    # ambiguity!!!
                    import warnings
                    
                    message = 'The supplied parent and the project is not ' \
                              'matching in %s, Stalker will use the parent ' \
                              'project (%s) as the parent of this %s' % \
                              (self,
                               self.parent._project,
                               self.__class__.__name__)
                    
                    warnings.warn(message, RuntimeWarning)
                    
                    # use the parent.project
                    project = self.parent._project
        
        return project
    
    @validates("priority")
    def _validate_priority(self, key, priority):
        """validates the given priority value
        """
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            pass
        
        if not isinstance(priority, int):
            priority = defaults.TASK_PRIORITY
        
        if priority < 0:
            priority = 0
        elif priority > 1000:
            priority = 1000
        
        return priority
    
    @validates('children')
    def _validate_children(self, key, child):
        """validates the given child
        """
        # just empty the resources list
        self.resources = []
        
        # extend the start and end dates
        #if not len(self.children): # it is not a good idea to load the
        #                           # collection here
        #    self.start = child.start
        #    self.end = child.end
        #else:
        #    # this is not the first one just extend the start and end
        #    if child.start < self.start:
        #        self.start = child.start
        #    if child.end > self.end:
        #        self.end = child.end
        
        # check for CircularDependency
        #_check_circular_dependency(self, child, 'children')
        
        return child
    
    @validates("resources")
    def _validate_resources(self, key, resource):
        """validates the given resources value
        """
        from stalker.models.auth import User
        if not isinstance(resource, User):
            raise TypeError("Task.resources should be a list of "
                            "stalker.models.auth.User instances not %s" %
                            resource.__class__.__name__)
        
            ## milestones do not need resources
            #if self.is_milestone:
            #resource = None
        
        return resource
    
    @validates("versions")
    def _validate_versions(self, key, version):
        """validates the given version value
        """
        from stalker.models.version import Version
        
        if not isinstance(version, Version):
            raise TypeError("Task.versions should only have "
                            "stalker.models.version.Version instances")
        
        return version
    
    def _duration_getter(self):
        return self._duration
    
    def _duration_setter(self, duration):
        # just call the fset method of the duration property in the super
        
        #------------------------------------------------------------
        # code copied and pasted from ScheduleMixin - Fix it later
        if duration is not None:
            if isinstance(duration, datetime.timedelta):
                # set the end to None
                # to make it recalculated
                self._validate_dates(self.start, None, duration)
            else:
                self._validate_dates(self.start, self.end, duration)
        else:
            self._validate_dates(self.start, self.end, duration)
        #------------------------------------------------------------
        
        # then update the effort
        num_of_resources = len(self.resources)
        if num_of_resources == 0:
            num_of_resources = 1
        
        new_effort_value = self.duration * num_of_resources
        
        # break recursion
        if self.effort != new_effort_value:
            self.effort = new_effort_value
    
    duration = synonym(
        "_duration",
        descriptor=property(
            _duration_getter,
            _duration_setter
        ),
        doc="""The overridden duration attribute.
        
        It is a datetime.timedelta instance. Showing the difference of the
        :attr:`~stalker.models.mixins.ScheduleMixin.start` and the
        :attr:`~stalker.models.mixins.ScheduleMixin.end`. If edited it
        changes the :attr:`~stalker.models.mixins.ScheduleMixin.end`
        attribute value.
        """
    )
    
    def _start_getter(self):
        """overridden start getter
        """
        # TODO: do it only once not all the time they ask for it
        # use children start
        if self.is_container:
            self._start = datetime.datetime.max
            for child in self.children:
                if child.start < self._start:
                    self._start = child.start
        return self._start
    
    def _start_setter(self, start_in):
        """overridden start setter
        """
        # update the start only if this is not a container task
        if self.is_leaf:
            self._validate_dates(start_in, self.end, self.duration)
    
    @declared_attr
    def start(self):
        return synonym(
            '_start',
            descriptor=property(
                self._start_getter,
                self._start_setter,
                doc="""The overridden start property.
                
                The start of the Task can not be changed if it is a container task.
                Works normally in other case.
                """
            )
        )
    
    def _end_getter(self):
        """overridden end getter
        """
        # TODO: do it only once not all the time they ask for it
        # use children end
        if self.is_container:
            self._end = datetime.datetime.min
            for child in self.children:
                if child.end > self._end:
                    self._end = child.end
        return self._end
    
    def _end_setter(self, end_in):
        """overridden end setter
        """
        # update the end only if this is not a container task
        if self.is_leaf:
            self._validate_dates(self.start, end_in, self.duration)
    
    @declared_attr
    def end(self):
        return synonym(
            '_end',
            descriptor=property(
                self._end_getter,
                self._end_setter,
                doc="""The overridden end property.
                
                The end of the Task can not be changed if it is a container task.
                Works normally in other cases.
                """
            )
        )
    
    def _project_getter(self):
        return self._project
    
    project = synonym(
        '_project',
        descriptor=property(
            _project_getter
        ),
        doc="""The owner Project of this task.
        
        It is a read-only attribute. It is not possible to change the owner
        Project of a Task it is defined when the Task is created.
        """
    )
    
    @property
    def is_container(self):
        """Returns True if the Task has children Tasks
        """
        return bool(len(self.children))
    
    @property
    def is_leaf(self):
        """Returns True if the Task has no children Tasks
        """
        return not bool(len(self.children))
    
    
    @property
    def level(self):
        """Returns the level of this task. It is a temporary property and will
        be useless when Stalker has its own implementation of a proper Gantt
        Chart. Write now it is used by the jQueryGantt.
        """
        i=0
        current = self
        while current:
            i+=1
            current = current.parent
        return i

def _check_circular_dependency(task, check_for_task, attr_name):
    """checks the circular dependency in task if it has check_for_task in its
    depends list
    """
    for dependent_task in getattr(task, attr_name): #depends:
        if dependent_task is check_for_task:
            raise CircularDependencyError(
                'task %s and %s creates a circular dependency' %
                (task, check_for_task)
            )
        else:
            _check_circular_dependency(
                dependent_task, check_for_task, attr_name
            )

# TASK_DEPENDENCIES
Task_Dependencies = Table(
    "Task_Dependencies", Base.metadata,
    Column("task_id", Integer, ForeignKey("Tasks.id"), primary_key=True),
    Column("depends_to_task_id", Integer, ForeignKey("Tasks.id"),
           primary_key=True)
)

# TASK_RESOURCES
Task_Resources = Table(
    "Task_Resources", Base.metadata,
    Column("task_id", Integer, ForeignKey("Tasks.id"), primary_key=True),
    Column("resource_id", Integer, ForeignKey("Users.id"), primary_key=True)
)


# TODO: subscribe to task: Users should be able to subscribe to any task they
#       want so they can be informed about the tickets as if they are a
#       resource for that task.
