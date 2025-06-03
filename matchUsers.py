import random
import numpy as np
from itertools import combinations
from sklearn.metrics.pairwise import cosine_similarity

# Skill mappings for encoding
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

# Convert answer to index
def skill_to_index(question, answer):
    return skill_maps[question].index(answer)

# One-hot encode skills
def encode_user_skills(skills):
    vector = []
    for q in ["q1", "q2", "q3", "q4", "q5"]:
        idx = skill_to_index(q, skills[q])
        one_hot = [0] * len(skill_maps[q])
        one_hot[idx] = 1
        vector.extend(one_hot)
    return np.array(vector)

# Cosine similarity of style (q3-q5)
def style_similarity(vecs):
    q3_offset = len(skill_maps["q1"]) + len(skill_maps["q2"])
    style_vecs = [v[q3_offset:] for v in vecs]
    sim_matrix = cosine_similarity(style_vecs)
    return (sim_matrix[0,1] + sim_matrix[0,2] + sim_matrix[1,2]) / 3.0

# Group scoring function
def group_score(group_data):
    group_vecs = [encode_user_skills(u["skills"]) for u in group_data]
    q1_roles = [u["skills"]["q1"] for u in group_data]
    q1_diversity = len(set(q1_roles)) / 3.0
    q2_same = len(set(u["skills"]["q2"] for u in group_data)) == 1
    sim_score = style_similarity(group_vecs)
    return 0.4 * q1_diversity + 0.3 * q2_same + 0.3 * sim_score

# Create optimal groups of 3
def full_grouping_with_role_diversity(user_json):
    users = list(user_json.items())
    valid_triplets = []

    # Step 1: Generate all valid triplets with unique roles
    for triplet in combinations(users, 3):
        roles = [u[1]["skills"]["q1"] for u in triplet]
        if len(set(roles)) == 3:
            group_data = [u[1] for u in triplet]
            score = group_score(group_data)
            valid_triplets.append((score, triplet))

    # Step 2: Sort triplets by descending score
    valid_triplets.sort(reverse=True, key=lambda x: x[0])

    used_ids = set()
    final_groups = {}
    group_num = 1

    # Step 3: Greedily pick best non-overlapping groups
    for score, triplet in valid_triplets:
        ids = [u[0] for u in triplet]
        if any(uid in used_ids for uid in ids):
            continue
        group_entry = {
            f"group {group_num}": {
                "members": {
                    u[0]: {  # u[0] is the user_id
                        "name": u[1]["name"],
                        "skills": list(u[1]["skills"].values())
                    } for u in triplet
                }
            }
        }
        final_groups.update(group_entry)
        used_ids.update(ids)
        group_num += 1

    return final_groups


def run_matching(user_json):
    return full_grouping_with_role_diversity(user_json)