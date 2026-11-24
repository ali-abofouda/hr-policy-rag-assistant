"""backend/eval/dataset.py — Golden Evaluation Dataset and Loaders."""

from typing import Dict, List

GOLDEN_EVALUATION_DATASET: List[Dict[str, str]] = [
    {
        "question": "What is the standard policy regarding annual leave entitlement?",
        "answer": "Every full-time employee is entitled to 18 days of paid annual leave per calendar year, accrued at a rate of 1.5 days per completed month of service.",
    },
    {
        "question": "Can I carry forward unused annual leave days to the next calendar year?",
        "answer": "Yes, unused annual leave may be carried forward to the next calendar year up to a maximum of 10 days; any remaining balance beyond that is forfeited on December 31st.",
    },
    {
        "question": "What is the required notice period during the probation period?",
        "answer": "During the probation period, either the employee or the company may terminate the employment relationship with 15 days' written notice, or payment in lieu of notice.",
    },
    {
        "question": "What is the standard notice period for confirmed permanent employees?",
        "answer": "The standard notice period for confirmed permanent employees is 60 days (2 calendar months) for both resignation by the employee and termination initiated by the company, except in cases of termination for cause.",
    },
    {
        "question": "How many days per week am I allowed to work from home?",
        "answer": "Eligible employees in approved roles may work from home for up to 2 days per week, subject to manager approval.",
    },
    {
        "question": "What is the paid maternity leave duration?",
        "answer": "Employees who give birth are entitled to 26 weeks of paid maternity leave, which may begin up to 8 weeks before the expected delivery date.",
    },
    {
        "question": "How many days of paid paternity leave do new fathers receive?",
        "answer": "Employees whose partner gives birth are entitled to 2 weeks of paid paternity leave, to be taken within 3 months of the child's birth (may be split into two blocks with manager approval).",
    },
    {
        "question": "What is the policy for taking sick leave and when is a medical certificate needed?",
        "answer": "Employees are entitled to 10 days of paid sick leave per calendar year (does not carry forward). For sick leave of 3 or more consecutive days, a medical certificate must be submitted to HR within 5 working days of returning to work.",
    },
    {
        "question": "What internet reimbursement amount can remote employees claim monthly?",
        "answer": "Employees with a standing work-from-home arrangement may claim up to 1,500 (local currency) per month toward internet costs, provided these are used substantially for work purposes.",
    },
    {
        "question": "What are the requirements for completing the employee exit clearance process?",
        "answer": "The clearance process includes resignation submission, handover of ongoing projects and documentation to a colleague/successor at least 10 days before the last day, return of all company-issued assets (laptops, access cards, mobile devices, physical documents), an optional exit interview, IT access revocation at 11:59 PM on the last day, and final settlement within 45 days.",
    },
]


def get_golden_dataset() -> List[Dict[str, str]]:
    """Return the golden evaluation question-answer pairs."""
    return GOLDEN_EVALUATION_DATASET
