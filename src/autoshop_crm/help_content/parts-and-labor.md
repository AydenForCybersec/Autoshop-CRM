# Tracking Parts and Labor

After you create a job, you need to record what parts were used and who worked on it. This is what builds the invoice — the system adds everything up automatically.

## Adding parts to a job

Open the vehicle page. Find the job in the list on the left. Scroll down inside that job to the **Parts Used** section.

Fill in the form below the parts list:

- **Part Name** — what the part is. For example: `Oil Filter`, `Front Brake Pads`, `Serpentine Belt`.
- **Price ($)** — what you are charging the customer for this part. Type the dollar amount, like `14.99` or `129.00`. Do not type the dollar sign.
- **Supplier** — where you got it. For example: `AutoZone` or `NAPA`. Optional.
- **Warranty Years** — if the part has a warranty, enter the number of years. For example: `2`. Leave blank if no warranty.
- **Purchased Date** — when you bought or installed the part. Leave blank to use today.
- **Notes** — any extra notes, like a receipt number. Optional.

Click **Add Part**. The part will appear in the list above with its price shown.

You can add as many parts as you need. Each one shows up as its own line on the invoice.

## Logging labor hours

Scroll down past the parts section on the same job. You will see a **Labor** section.

Fill in the form:

- **Mechanic** — click the dropdown and pick who did the work. The system shows each mechanic's hourly rate next to their name so you know what will be charged.
- **Hours** — how many hours they worked on this job. You can use decimals. For example: `1.5` means one and a half hours. `0.5` means half an hour.
- **Notes** — optional description of what was done. For example: `Replaced front pads, resurfaced rotors`.

Click **Log Labor**. The entry will appear above with the total cost calculated automatically (hours × their hourly rate).

You can log labor from multiple mechanics on the same job. For example, if one mechanic did the diagnosis and another did the repair, add a separate entry for each.

## How the price is calculated

The system adds everything up for you:

- **Parts total** — the sum of every part's price
- **Labor total** — the sum of every mechanic's hours × their hourly rate
- **Subtotal** — parts + labor combined
- **Tax** — applied automatically based on your shop's tax rate setting
- **Card fee** — added only if the customer pays by card (you toggle this on the invoice)
- **Total Due** — the final number the customer owes

You do not need a calculator. Just enter the parts and hours and the system does the math.

## Setting mechanic labor rates

If a mechanic's rate is missing or wrong, an owner or admin can fix it. Go to **Settings** in the top menu, click the **Users** tab, find the mechanic's name, and enter their hourly rate in the **Labor Rate ($/hr)** box. Click **Update User**.

The rate is recorded at the time you log the labor. If you change a mechanic's rate later, old entries keep the original rate — so history stays accurate.

## Warranty tracking

When you enter a warranty on a part, the system remembers it. If a customer comes back and that warranty is still active, it will show up at the top of the vehicle page under **Active Warranty Coverage** so you can see it right away without digging through old jobs.
