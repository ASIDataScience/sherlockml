# Copyright 2018-2019 Faculty Science Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple
from enum import Enum

from marshmallow import fields, post_load
from marshmallow_enum import EnumField

from faculty.clients.base import BaseSchema, BaseClient


class ExperimentRunStatus(Enum):
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    SCHEDULED = "scheduled"


Experiment = namedtuple(
    "Experiment",
    [
        "id",
        "name",
        "description",
        "artifact_location",
        "created_at",
        "last_updated_at",
        "deleted_at",
    ],
)


ExperimentRun = namedtuple(
    "ExperimentRun",
    [
        "id",
        "experiment_id",
        "artifact_location",
        "status",
        "started_at",
        "ended_at",
        "deleted_at",
    ],
)

Page = namedtuple("Page", ["start", "limit"])
Pagination = namedtuple("Pagination", ["start", "size", "previous", "next"])
ListExperimentRunsResponse = namedtuple(
    "ListExperimentRunsResponse", ["runs", "pagination"]
)


class ExperimentSchema(BaseSchema):
    id = fields.Integer(data_key="experimentId", required=True)
    name = fields.String(required=True)
    description = fields.String(required=True)
    artifact_location = fields.String(
        data_key="artifactLocation", required=True
    )
    created_at = fields.DateTime(data_key="createdAt", required=True)
    last_updated_at = fields.DateTime(data_key="lastUpdatedAt", required=True)
    deleted_at = fields.DateTime(data_key="deletedAt", missing=None)

    @post_load
    def make_experiment(self, data):
        return Experiment(**data)


class ExperimentRunSchema(BaseSchema):
    id = fields.UUID(data_key="runId", required=True)
    experiment_id = fields.Integer(data_key="experimentId", required=True)
    artifact_location = fields.String(
        data_key="artifactLocation", required=True
    )
    status = EnumField(ExperimentRunStatus, by_value=True, required=True)
    started_at = fields.DateTime(data_key="startedAt", required=True)
    ended_at = fields.DateTime(data_key="endedAt", missing=None)
    deleted_at = fields.DateTime(data_key="deletedAt", missing=None)

    @post_load
    def make_experiment_run(self, data):
        return ExperimentRun(**data)


class PageSchema(BaseSchema):
    start = fields.Integer(required=True)
    limit = fields.Integer(required=True)

    @post_load
    def make_page(self, data):
        return Page(**data)


# TODO reuse pagination from jobs?
class PaginationSchema(BaseSchema):
    start = fields.Integer(required=True)
    size = fields.Integer(required=True)
    previous = fields.Nested(PageSchema, missing=None)
    next = fields.Nested(PageSchema, missing=None)

    @post_load
    def make_pagination(self, data):
        return Pagination(**data)


class ListExperimentRunsResponseSchema(BaseSchema):
    pagination = fields.Nested(PaginationSchema, required=True)
    runs = fields.Nested(ExperimentRunSchema, many=True, required=True)

    @post_load
    def make_list_runs_response_schema(self, data):
        return ListExperimentRunsResponse(**data)


class CreateRunSchema(BaseSchema):
    started_at = fields.DateTime(data_key="startedAt")
    artifact_location = fields.String(data_key="artifactLocation")


class ExperimentClient(BaseClient):

    SERVICE_NAME = "atlas"

    def create(
        self, project_id, name, description=None, artifact_location=None
    ):
        """Create an experiment.

        Parameters
        ----------
        project_id : uuid.UUID
        name : str
        description : str, optional
        artifact_location : str, optional

        Returns
        -------
        Experiment
        """
        endpoint = "/project/{}/experiment".format(project_id)
        payload = {
            "name": name,
            "description": description,
            "artifactLocation": artifact_location,
        }
        return self._post(endpoint, ExperimentSchema(), json=payload)

    def get(self, project_id, experiment_id):
        """Get a specified experiment.

        Parameters
        ----------
        project_id : uuid.UUID
        experiment_id : int

        Returns
        -------
        Experiment
        """
        endpoint = "/project/{}/experiment/{}".format(
            project_id, experiment_id
        )
        return self._get(endpoint, ExperimentSchema())

    def list(self, project_id):
        """List the experiments in a project.

        Parameters
        ----------
        project_id : uuid.UUID

        Returns
        -------
        List[Experiment]
        """
        endpoint = "/project/{}/experiment".format(project_id)
        return self._get(endpoint, ExperimentSchema(many=True))

    def create_run(
        self, project_id, experiment_id, started_at, artifact_location=None
    ):
        """Create a run in a project.

        Parameters
        ----------
        project_id : uuid.UUID
        experiment_id : int
        started_at : datetime.datetime
            Time at which the run was started. If the datetime does not have a
            timezone, it will be assumed to be in UTC.
        artifact_location: str, optional
            The location of the artifact repository to use for this run.
            If omitted, the value of `artifact_location` for the experiment
            will be used.

        Returns
        -------
        ExperimentRun
        """
        endpoint = "/project/{}/experiment/{}/run".format(
            project_id, experiment_id
        )
        payload = CreateRunSchema().dump(
            {"started_at": started_at, "artifact_location": artifact_location}
        )
        return self._post(endpoint, ExperimentRunSchema(), json=payload)

    def get_run(self, project_id, run_id):
        """Get a specified experiment run.

        Parameters
        ----------
        project_id : uuid.UUID
        run_id : uuid.UUID

        Returns
        -------
        ExperimentRun
        """
        endpoint = "/project/{}/run/{}".format(project_id, run_id)
        return self._get(endpoint, ExperimentRunSchema())

    def list_runs(
        self,
        project_id,
        experiment_ids=None,
        lifecycle_stage=None,
        start=None,
        limit=None,
    ):
        """List experiment runs.

        This method returns pages of runs. If less than the full number of runs
        for the job is returned, the ``next`` page of the returned response
        object will not be ``None``:

        >>> response = client.list_runs(project_id)
        >>> response.pagination.next
        Page(start=10, limit=10)

        Get all experiment runs by making successive calls to ``list_runs``,
        passing the ``start`` and ``limit`` of the ``next`` page each time
        until ``next`` is returned as ``None``.

        Parameters
        ----------
        project_id : uuid.UUID
        experiment_ids : List[int], optional
            To filter runs of experiments with the given IDs only. If an empty
            list is passed, a result with an empty list of runs is returned.
        start : int, optional
            The (zero-indexed) starting point of runs to retrieve.
        limit : int, optional
            The maximum number of runs to retrieve.

        Returns
        -------
        ListExperimentRunsResponse
        """
        if lifecycle_stage is not None:
            raise NotImplementedError("lifecycle_stage is not supported.")

        query_params = []
        if experiment_ids is not None:
            if len(experiment_ids) == 0:
                return ListExperimentRunsResponse(
                    runs=[],
                    pagination=Pagination(
                        start=0, size=0, previous=None, next=None
                    ),
                )
            for experiment_id in experiment_ids:
                query_params.append(("experimentId", experiment_id))

        if start is not None:
            query_params.append(("start", start))
        if limit is not None:
            query_params.append(("limit", limit))

        endpoint = "/project/{}/run".format(project_id)
        return self._get(
            endpoint, ListExperimentRunsResponseSchema(), params=query_params
        )
