import numpy as np
from itertools import combinations
from sklearn.metrics.pairwise import cosine_similarity

skill_maps = {
    "q1": ["Hacker", "Hustler", "Hipster", "Explorer"],
    "q2": [
        "Tech & Software", "Sustainability", "Health & Wellness", "Arts & Culture",
        "Business & Finance", "Education", "Social Impact & Community", "Open to Anything"
    ],
    "q3": [
        "Fast Paced and action-oriented", "Structured and planned",
        "Flexible and go-with-the-flow", "I adapt to the team's rhythm"
    ],
    "q4": [
        "Brainstorming new ideas", "Seeing tangible progress",
        "Collaborating with others", "Solving hard problems"
    ],
    "q5": [
        "I lead and organize ideas", "I analyze and critique proposals",
        "I bring creative, out-of-the-box ideas", "Listen and support others' contributions"
    ]
}

def encode_user_from_model(user):
    answers = {a.question_id: a.answer for a in user.answers}
    vector = []
    for q in ["q1", "q2", "q3", "q4", "q5"]:
        idx = skill_maps[q].index(answers[q])
        one_hot = [0] * len(skill_maps[q])
        one_hot[idx] = 1
        vector.extend(one_hot)
    return np.array(vector)

def sqlalchemy_grouping(users):
    user_data = []
    for user in users:
        answers = {a.question_id: a.answer for a in user.answers}
        if len(answers) < 5:
            continue
        user_data.append({
            'id': user.id,
            'name': user.name,
            'college': user.college,
            'skills': user.skills,
            'answers': answers,
            'vector': encode_user_from_model(user),
            'user_obj': user
        })

    used_ids = set()
    final_groups = {}
    group_num = 1

    def group_score(vecs, roles, interests):
        q1_diversity = len(set(roles)) / 3.0
        q2_same = len(set(interests)) == 1
        q3_offset = len(skill_maps["q1"]) + len(skill_maps["q2"])
        style_vecs = [v[q3_offset:] for v in vecs]
        sim_score = cosine_similarity(style_vecs).mean()
        return 0.4 * q1_diversity + 0.3 * q2_same + 0.3 * sim_score

    triplets = combinations(user_data, 3)
    scored_triplets = []

    for triplet in triplets:
        ids = [u['id'] for u in triplet]
        if any(uid in used_ids for uid in ids):
            continue
        roles = [u['answers']['q1'] for u in triplet]
        if len(set(roles)) < 3:
            continue
        vectors = [u['vector'] for u in triplet]
        interests = [u['answers']['q2'] for u in triplet]
        score = group_score(vectors, roles, interests)
        scored_triplets.append((score, triplet))

    scored_triplets.sort(reverse=True, key=lambda x: x[0])

    for score, triplet in scored_triplets:
        ids = [u['id'] for u in triplet]
        if any(uid in used_ids for uid in ids):
            continue
        final_groups[f"group-{group_num}"] = {
            "members": {
                u['name']: {
                    "name": u['name'],
                    "skills": list(u['answers'].values())
                } for u in triplet
            },
            "user_objs": [u['user_obj'] for u in triplet]
        }
        used_ids.update(ids)
        group_num += 1

    remaining = [u for u in user_data if u['id'] not in used_ids]
    if remaining:
        final_groups[f"group-{group_num}"] = {
            "members": {
                u['name']: {
                    "name": u['name'],
                    "skills": list(u['answers'].values())
                } for u in remaining
            },
            "user_objs": [u['user_obj'] for u in remaining]
        }

    return final_groups

def run_matching_sqlalchemy(users):
    return sqlalchemy_grouping(users)
