import os
import batchman

batch = batchman.load_batch(unique_id="1221", name="past-exxa")

for result in batch.get_results():
    print(result.choices[0].message.content)