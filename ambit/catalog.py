"""
The permission catalogue, in the console's own words.

Django knows "course_offering.add_courseoffering"; an IT administrator
building a role knows "Subjects in a section -- add". This maps one to
the other, grouped the way the console is grouped, so the role form can
draw a matrix instead of a 200-row multi-select. Permissions not listed
here (admin log entries, sessions, content types...) are simply not
offered -- and a role that already carries one keeps it untouched.
"""

from dataclasses import dataclass

from django.contrib.auth.models import Permission

ACTIONS = ("view", "add", "change", "delete")
ACTION_LABELS = {"view": "See", "add": "Add", "change": "Change", "delete": "Remove"}


@dataclass(frozen=True)
class Entry:
    app_label: str
    model: str
    label: str
    hint: str = ""
    # Some things have no meaningful add/delete from the console.
    actions: tuple = ACTIONS
    # A custom permission shown in one of the four columns: {"change":
    # "mark_exam_submission"} draws "Exam marks -- Change" as its own row.
    codenames: tuple = ()

    @property
    def key(self):
        return f"{self.app_label}.{self.model}"

    def codename(self, action):
        return dict(self.codenames).get(action) or f"{action}_{self.model}"


CATALOG = [
    ("School structure", [
        Entry("school", "schoolprofile", "School identity", "Name, logo, colour, contact details.", actions=("view", "change")),
        Entry("academic_year", "academicyear", "Academic years"),
        Entry("stage", "stage", "Stages"),
        Entry("grade", "grade", "Grades"),
        Entry("department", "department", "Departments"),
        Entry("subject", "subject", "Subjects", "A grade's subjects are its curriculum."),
        Entry("classroom", "classroom", "Sections", "Grade 2 · A: a class of students."),
        Entry("school_calendar", "term", "Terms", "Everyone can see the calendar; this is who may change it."),
        Entry("school_calendar", "calendarentry", "Calendar entries", "Holidays, closures, exams, events."),
    ]),
    ("Teaching", [
        Entry("course_offering", "courseoffering", "Subjects in a section"),
        Entry("teacher_assignment", "teacherassignment", "Teacher assignments", "Who teaches what."),
        Entry("scheduling", "schoolweek", "School week", actions=("view", "change")),
        Entry("scheduling", "period", "Periods", "The bell schedule."),
        Entry("scheduling", "lesson", "Timetable lessons"),
        Entry("scheduling", "teacherabsence", "Teacher absences"),
        Entry("scheduling", "cover", "Cover", "Who takes an absent teacher's lesson."),
    ]),
    ("Attendance", [
        Entry("attendance", "register", "Registers", "Taking attendance for a lesson; Own teaching reaches a teacher's own."),
        Entry("attendance", "attendanceentry", "Absence follow-up", "Justifying an absence after hearing from the family.", actions=("change",)),
        Entry("attendance", "attendancepolicy", "Attendance thresholds", "When a student is flagged.", actions=("change",)),
    ]),
    ("Behaviour", [
        Entry("behaviour", "behaviourrecord", "Incidents & recognitions", "What a student did that was worth writing down."),
        Entry("behaviour", "category", "Behaviour categories", "The school's own words for it.", actions=("view", "add", "change")),
        Entry("behaviour", "behaviourpolicy", "Behaviour thresholds", "When a student is flagged.", actions=("change",)),
    ]),
    ("Support", [
        Entry("interventions", "intervention", "Intervention cycles", "What the school does about a flag -- owner, goal, reviews, outcome. Change covers reviewing and closing."),
    ]),
    ("Badges", [
        Entry("badges", "badge", "Badges", "What the records earned a student: the catalogue, a section's board, her card. Read only by design -- nobody hands a badge out.", actions=("view",)),
    ]),
    ("Year end", [
        Entry("promotion", "decision", "Year end", "Who moves up, repeats or leaves at year end. Add = decide and apply; the policy's word stands unless overruled with a reason.", actions=("view", "add")),
        Entry("promotion", "promotionpolicy", "Pass and fail criteria", "The bar a student must reach to move up.", actions=("change",)),
    ]),
    ("Analysis", [
        Entry("insights", "insightsettings", "Analysis", "The numbers per stage, grade, section, student and teacher, over the sections this reaches (every subject in them). The Teachers tab opens for a stage, department or school grant only. Change = the targets and default window.", actions=("view", "change"), codenames=(("view", "view_analysis"),)),
    ]),
    ("Activities", [
        Entry("activities", "activity", "Activities", "The clubs, teams and groups the school runs.", actions=("view", "add", "change")),
        Entry("activities", "participation", "Taking part", "Who is in which activity, and what they achieved. Needs Activities · See to open an activity's page."),
    ]),
    ("Learning", [
        Entry("assessment", "assignment", "Work set", "Homework, classwork, projects, quizzes and exams set for a section. Editing or removing an exam needs this over a department, stage or the school."),
        Entry("assessment", "submission", "Marks", "Recording marks, feedback, late and missing work on ordinary assignments and quizzes.", actions=("view", "change")),
        Entry(
            "assessment", "submission", "Exam marks",
            "Marking exams. Given in a department, any of its teachers may mark any of its exams, in every section.",
            actions=("change",), codenames=(("change", "mark_exam_submission"),),
        ),
        Entry("assessment", "gradingscheme", "Grading scheme", "Letter bands, and how much missing work flags a student.", actions=("change",)),
        Entry("assessment", "reporttemplate", "Report templates", "School-wide report headings, sections and footer text.", actions=("view", "add", "change")),
        Entry("assessment", "studentreport", "Student reports", "School-wide access to complete student report snapshots. Change allows submitting drafts for review.", actions=("view", "add", "change")),
        Entry("assessment", "studentreport", "Review reports", "Return reports with requested changes. Requires school-wide report visibility.", actions=("change",), codenames=(("change", "review_studentreport"),)),
        Entry("assessment", "studentreport", "Approve reports", "Approve complete reports after review. Approval does not publish.", actions=("change",), codenames=(("change", "approve_studentreport"),)),
        Entry("assessment", "studentreport", "Publish reports", "Release approved reports to currently linked families. Requires school-wide report visibility.", actions=("change",), codenames=(("change", "publish_studentreport"),)),
        Entry("assessment", "studentreport", "Correct published reports", "Start a correction; the original remains visible until the correction is reviewed, approved and published.", actions=("change",), codenames=(("change", "correct_studentreport"),)),
        Entry("assessment", "assessmentstructure", "Assessment structures", "Configure subject and term weights by academic year, within a department or stage.", actions=("view", "add", "change")),
        Entry("assessment", "reportcomment", "Report comments", "Read, add or edit source comments within a department or stage. Saved reports are unchanged.", actions=("view", "add", "change")),
    ]),
    ("Family", [
        Entry("communications", "contact", "Family contacts", "What the school said to a family, and when.", actions=("view", "add", "change")),
        Entry(
            "communications", "thread", "Family conversations",
            "Messaging a student's family in the parent portal. View = read the conversations; add = open one and reply; change = close it, or log it as a contact.",
            actions=("view", "add", "change"),
        ),
        Entry("family", "absenceexplanation", "Explanations from families", "What a family sent about a day away, through the parent portal. Change = accept (justifying that day's absences) or decline with a line back.", actions=("view", "change")),
    ]),
    ("Finance", [
        Entry("finance", "journalentry", "General ledger",
              "Reading the school's books, and posting to them. Finance staff only: these pages live in their own portal.",
              actions=("view",), codenames=(("view", "view_ledger"),)),
        Entry("finance", "journalentry", "Posting to the ledger",
              "Writing a transaction, or reversing one. Never edits: a correction is its own entry.",
              actions=("add",), codenames=(("add", "post_journal"),)),
        Entry("finance", "account", "Chart of accounts", "The accounts the school keeps its books in.",
              actions=("view", "add", "change")),
        Entry("finance", "costcenter", "Cost centres", "What a cost belongs to, for budgets and reporting."),
        Entry("finance", "feestructure", "Fee price list", "What each grade pays, per year.", actions=("view", "add", "change")),
        Entry("finance", "feecomponent", "Fee components", "Tuition, transport, books -- and which revenue account each lands in.", actions=("view", "add", "change")),
        Entry("finance", "discountrule", "Discount rules", "Sibling rates, staff rates, financial aid.", actions=("view", "add", "change")),
        Entry("finance", "paymentscheduletemplate", "Payment schedules", "Whether fees fall due in instalments or all at once.", actions=("view", "add", "change")),
        Entry("finance", "studentpaymentplan", "Student fee plans", "Working out and agreeing what one family owes for the year.", actions=("view", "add")),
        Entry("finance", "payment", "Payments from families", "The proof a family uploads, and the queue it waits in.", actions=("view", "add")),
        Entry("finance", "payment", "Verifying payments",
              "Accepting or refusing a payment. Accepting posts it to the ledger and issues the receipt, so it is its own grant.",
              actions=("change",), codenames=(("change", "verify_payment"),)),
        Entry("finance", "officialreceipt", "Receipts", actions=("view",)),
        Entry("finance", "payment", "Reversing verified payments",
              "Correct a verified payment and its ledger entry together. Also requires posting to the ledger.",
              actions=("change",), codenames=(("change", "reverse_payment"),)),
        Entry("finance", "studentpaymentplan", "Correcting a bill",
              "Putting right what a family was billed, after the bill is out. Corrections are new "
              "rows, never edits, so this is its own grant.",
              actions=("change",), codenames=(("change", "adjust_studentpaymentplan"),)),
        Entry("finance", "supplier", "Suppliers", "Who the school buys from.",
              actions=("view", "add", "change")),
        Entry("finance", "expense", "Costs", "Recording what the school spends.",
              actions=("view", "add")),
        Entry("finance", "budget", "Budget",
              "What the school means to spend, against what it has. Change = setting the figures.",
              actions=("view", "change")),
        Entry("finance", "salarystructure", "What people are paid",
              "Setting an employee's monthly salary.", actions=("view", "add")),
        Entry("finance", "payrollrun", "Payroll", "Working up a month's pay.",
              actions=("view", "add")),
        Entry("finance", "payrollrun", "Approving payroll",
              "Putting a month's pay into the books, and reopening it.",
              actions=("change",), codenames=(("change", "approve_payrollrun"),)),
        Entry("finance", "payrollrun", "Paying payroll",
              "Handing the net over to staff, which takes money out of the school.",
              actions=("change",), codenames=(("change", "pay_payrollrun"),)),
        Entry("finance", "expense", "Paying suppliers",
              "Taking money out of the school to settle a bill, and reversing a cost.",
              actions=("change",), codenames=(("change", "pay_expense"),)),
    ]),
    ("People", [
        Entry("teacher", "teacher", "Teachers"),
        Entry("teacher", "employee", "Employees", "Everyone the school employs, including non-teaching staff."),
        Entry(
            "teacher", "employee", "Which portal an employee works in",
            "Moves a login between the academic app, finance and the owner's overview. The strongest change in the "
            "school: it is never part of the administrator role and has to be granted on purpose.",
            actions=("change",), codenames=(("change", "change_portal"),),
        ),
        Entry("student", "student", "Students"),
        Entry("student", "enrollment", "Enrolments", "Which section a student is in this year."),
        Entry("student", "electivechoice", "Elective choices", "Which elective a student takes this year.", actions=("change",)),
        Entry("student", "studentmedicalinfo", "Medical information", actions=("view", "change")),
        Entry("student", "guardian", "Guardians"),
        Entry("student", "studentguardian", "Student–guardian links"),
    ]),
    ("Access", [
        Entry("users", "user", "Logins"),
        Entry("authorization", "role", "Roles"),
        Entry("authorization", "scope", "Who has access where", "The list of places access has been given in.", actions=("view", "change")),
        Entry("authorization", "roleassignment", "Give access", "A login gets a role somewhere: \"Heba is a Department Head in Mathematics\"."),
        Entry("audit", "auditentry", "Activity log", "Who changed what, when.", actions=("view",)),
    ]),
]


def entries():
    for _, group in CATALOG:
        yield from group


def catalog_permissions():
    """{(app_label, codename): Permission} for everything the catalogue offers."""
    wanted = {}
    for entry in entries():
        for action in entry.actions:
            wanted[(entry.app_label, entry.codename(action))] = None
    found = Permission.objects.filter(
        content_type__app_label__in={a for a, _ in wanted},
    ).select_related("content_type")
    for permission in found:
        key = (permission.content_type.app_label, permission.codename)
        if key in wanted:
            wanted[key] = permission
    return {key: perm for key, perm in wanted.items() if perm is not None}


def describe(permission):
    """"Classrooms · Add" for a catalogued permission, else the raw codename."""
    for entry in entries():
        if entry.app_label == permission.content_type.app_label:
            for action in entry.actions:
                if permission.codename == entry.codename(action):
                    return f"{entry.label} · {ACTION_LABELS[action]}"
    return f"{permission.content_type.app_label}.{permission.codename}"
