from submissions.repositories import SubmissionDocumentRepository


def iter_submission_files(submission):
    document_repository = SubmissionDocumentRepository()
    for document in document_repository.list_for_submission(submission):
        yield document.file
