# Copyright 2018 ASI Data Science
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

from datetime import datetime
from uuid import uuid4

import pytest
from dateutil.tz import UTC
from marshmallow import ValidationError

from sherlockml.clients.job import (
    JobMetadata,
    JobMetadataSchema,
    JobSummary,
    JobSummarySchema,
    JobClient,
    RunIdSchema,
    Page,
    PageSchema,
    Pagination,
    PaginationSchema,
    RunSummary,
    RunSummarySchema,
    RunState,
    SubrunSummary,
    SubrunSummarySchema,
    SubrunState,
    Run,
    RunSchema,
    ListRunsResponse,
    ListRunsResponseSchema,
)
from tests.clients.fixtures import PROFILE

PROJECT_ID = uuid4()
JOB_ID = uuid4()
RUN_ID = uuid4()
SUBRUN_ID = uuid4()

JOB_METADATA = JobMetadata(name="job name", description="job description")
JOB_METADATA_BODY = {
    "name": JOB_METADATA.name,
    "description": JOB_METADATA.description,
}

JOB_SUMMARY = JobSummary(id=JOB_ID, metadata=JOB_METADATA)
JOB_SUMMARY_BODY = {"jobId": str(JOB_ID), "meta": JOB_METADATA_BODY}

PAGE = Page(start=3, limit=10)
PAGE_BODY = {"start": PAGE.start, "limit": PAGE.limit}

PAGINATION = Pagination(
    start=20,
    size=10,
    previous=Page(start=10, limit=10),
    next=Page(start=30, limit=10),
)
PAGINATION_BODY = {
    "start": PAGINATION.start,
    "size": PAGINATION.size,
    "previous": {
        "start": PAGINATION.previous.start,
        "limit": PAGINATION.previous.limit,
    },
    "next": {"start": PAGINATION.next.start, "limit": PAGINATION.next.limit},
}

SUBMITTED_AT = datetime(2018, 3, 10, 11, 32, 6, 247000, tzinfo=UTC)
SUBMITTED_AT_STRING = "2018-03-10T11:32:06.247Z"
STARTED_AT = datetime(2018, 3, 10, 11, 32, 30, 172000, tzinfo=UTC)
STARTED_AT_STRING = "2018-03-10T11:32:30.172Z"
ENDED_AT = datetime(2018, 3, 10, 11, 37, 42, 482000, tzinfo=UTC)
ENDED_AT_STRING = "2018-03-10T11:37:42.482Z"

RUN_SUMMARY = RunSummary(
    id=RUN_ID,
    run_number=3,
    state=RunState.COMPLETED,
    submitted_at=SUBMITTED_AT,
    started_at=STARTED_AT,
    ended_at=ENDED_AT,
)
RUN_SUMMARY_BODY = {
    "runId": str(RUN_ID),
    "runNumber": RUN_SUMMARY.run_number,
    "state": "completed",
    "submittedAt": SUBMITTED_AT_STRING,
    "startedAt": STARTED_AT_STRING,
    "endedAt": ENDED_AT_STRING,
}

SUBRUN_SUMMARY = SubrunSummary(
    id=SUBRUN_ID,
    subrun_number=1,
    state=SubrunState.COMMAND_SUCCEEDED,
    started_at=STARTED_AT,
    ended_at=ENDED_AT,
)
SUBRUN_SUMMARY_BODY = {
    "subrunId": str(SUBRUN_ID),
    "subrunNumber": SUBRUN_SUMMARY.subrun_number,
    "state": "command-succeeded",
    "startedAt": STARTED_AT_STRING,
    "endedAt": ENDED_AT_STRING,
}

RUN = Run(
    id=RUN_ID,
    run_number=3,
    state=RunState.COMPLETED,
    submitted_at=SUBMITTED_AT,
    started_at=STARTED_AT,
    ended_at=ENDED_AT,
    subruns=[SUBRUN_SUMMARY],
)
RUN_BODY = {
    "runId": str(RUN_ID),
    "runNumber": RUN_SUMMARY.run_number,
    "state": "completed",
    "submittedAt": SUBMITTED_AT_STRING,
    "startedAt": STARTED_AT_STRING,
    "endedAt": ENDED_AT_STRING,
    "subruns": [SUBRUN_SUMMARY_BODY],
}

LIST_RUNS_RESPONSE = ListRunsResponse(
    runs=[RUN_SUMMARY], pagination=PAGINATION
)
LIST_RUNS_RESPONSE_BODY = {
    "runs": [RUN_SUMMARY_BODY],
    "pagination": PAGINATION_BODY,
}


def test_job_metadata_schema():
    data = JobMetadataSchema().load(JOB_METADATA_BODY)
    assert data == JOB_METADATA


def test_job_summary_schema():
    data = JobSummarySchema().load(JOB_SUMMARY_BODY)
    assert data == JOB_SUMMARY


def test_run_id_schema():
    data = RunIdSchema().load({"runId": str(RUN_ID)})
    assert data == RUN_ID


def test_page_schema():
    data = PageSchema().load(PAGE_BODY)
    assert data == PAGE


def test_pagination_schema():
    data = PaginationSchema().load(PAGINATION_BODY)
    assert data == PAGINATION


@pytest.mark.parametrize("field", ["previous", "next"])
def test_pagination_schema_nullable_field(field):
    body = PAGINATION_BODY.copy()
    del body[field]
    data = PaginationSchema().load(body)
    assert getattr(data, field) is None


def test_run_summary_schema():
    data = RunSummarySchema().load(RUN_SUMMARY_BODY)
    assert data == RUN_SUMMARY


@pytest.mark.parametrize(
    "data_key, field", [("startedAt", "started_at"), ("endedAt", "ended_at")]
)
def test_run_summary_schema_nullable_field(data_key, field):
    body = RUN_SUMMARY_BODY.copy()
    del body[data_key]
    data = RunSummarySchema().load(body)
    assert getattr(data, field) is None


def test_subrun_summary_schema():
    data = SubrunSummarySchema().load(SUBRUN_SUMMARY_BODY)
    assert data == SUBRUN_SUMMARY


@pytest.mark.parametrize(
    "data_key, field", [("startedAt", "started_at"), ("endedAt", "ended_at")]
)
def test_subrun_summary_schema_nullable_field(data_key, field):
    body = SUBRUN_SUMMARY_BODY.copy()
    del body[data_key]
    data = SubrunSummarySchema().load(body)
    assert getattr(data, field) is None


def test_run_schema():
    data = RunSchema().load(RUN_BODY)
    assert data == RUN


@pytest.mark.parametrize(
    "data_key, field", [("startedAt", "started_at"), ("endedAt", "ended_at")]
)
def test_run_schema_nullable_field(data_key, field):
    body = RUN_BODY.copy()
    del body[data_key]
    data = RunSchema().load(body)
    assert getattr(data, field) is None


def test_list_runs_response_schema():
    data = ListRunsResponseSchema().load(LIST_RUNS_RESPONSE_BODY)
    assert data == LIST_RUNS_RESPONSE


@pytest.mark.parametrize(
    "schema_class",
    [
        JobMetadataSchema,
        JobSummarySchema,
        RunIdSchema,
        PageSchema,
        PaginationSchema,
        RunSummarySchema,
        SubrunSummarySchema,
        RunSchema,
        ListRunsResponseSchema,
    ],
)
def test_schemas_invalid_data(schema_class):
    with pytest.raises(ValidationError):
        schema_class().load({})


def test_job_client_list(mocker):
    mocker.patch.object(JobClient, "_get", return_value=[JOB_SUMMARY])
    schema_mock = mocker.patch("sherlockml.clients.job.JobSummarySchema")

    client = JobClient(PROFILE)
    assert client.list(PROJECT_ID) == [JOB_SUMMARY]

    schema_mock.assert_called_once_with(many=True)
    JobClient._get.assert_called_once_with(
        "/project/{}/job".format(PROJECT_ID), schema_mock.return_value
    )


def test_job_client_create_run(mocker):
    mocker.patch.object(JobClient, "_post", return_value=RUN_ID)
    schema_mock = mocker.patch("sherlockml.clients.job.RunIdSchema")

    client = JobClient(PROFILE)
    assert (
        client.create_run(PROJECT_ID, JOB_ID, {"param": "one", "other": "two"})
        == RUN_ID
    )

    schema_mock.assert_called_once_with()
    JobClient._post.assert_called_once_with(
        "/project/{}/job/{}/run".format(PROJECT_ID, JOB_ID),
        schema_mock.return_value,
        json={
            "parameterValues": [
                [
                    {"name": "param", "value": "one"},
                    {"name": "other", "value": "two"},
                ]
            ]
        },
    )


def test_job_client_create_run_array(mocker):
    mocker.patch.object(JobClient, "_post", return_value=RUN_ID)
    schema_mock = mocker.patch("sherlockml.clients.job.RunIdSchema")

    client = JobClient(PROFILE)
    assert (
        client.create_run_array(
            PROJECT_ID,
            JOB_ID,
            [{"param": "one", "other": "two"}, {"param": "three"}],
        )
        == RUN_ID
    )

    schema_mock.assert_called_once_with()
    JobClient._post.assert_called_once_with(
        "/project/{}/job/{}/run".format(PROJECT_ID, JOB_ID),
        schema_mock.return_value,
        json={
            "parameterValues": [
                [
                    {"name": "param", "value": "one"},
                    {"name": "other", "value": "two"},
                ],
                [{"name": "param", "value": "three"}],
            ]
        },
    )


def test_job_client_list_runs(mocker):
    mocker.patch.object(JobClient, "_get", return_value=LIST_RUNS_RESPONSE)
    schema_mock = mocker.patch("sherlockml.clients.job.ListRunsResponseSchema")

    client = JobClient(PROFILE)
    assert client.list_runs(PROJECT_ID, JOB_ID) == LIST_RUNS_RESPONSE

    schema_mock.assert_called_once_with()
    JobClient._get.assert_called_once_with(
        "/project/{}/job/{}/run".format(PROJECT_ID, JOB_ID),
        schema_mock.return_value,
        params={},
    )


def test_job_client_list_runs_page(mocker):
    mocker.patch.object(JobClient, "_get", return_value=LIST_RUNS_RESPONSE)
    schema_mock = mocker.patch("sherlockml.clients.job.ListRunsResponseSchema")

    client = JobClient(PROFILE)
    assert (
        client.list_runs(PROJECT_ID, JOB_ID, start=20, limit=10)
        == LIST_RUNS_RESPONSE
    )

    schema_mock.assert_called_once_with()
    JobClient._get.assert_called_once_with(
        "/project/{}/job/{}/run".format(PROJECT_ID, JOB_ID),
        schema_mock.return_value,
        params={"start": 20, "limit": 10},
    )


def test_job_client_get_run(mocker):
    mocker.patch.object(JobClient, "_get", return_value=RUN)
    schema_mock = mocker.patch("sherlockml.clients.job.RunSchema")

    client = JobClient(PROFILE)
    assert client.get_run(PROJECT_ID, JOB_ID, RUN_ID) == RUN

    schema_mock.assert_called_once_with()
    JobClient._get.assert_called_once_with(
        "/project/{}/job/{}/run/{}".format(PROJECT_ID, JOB_ID, RUN_ID),
        schema_mock.return_value,
    )