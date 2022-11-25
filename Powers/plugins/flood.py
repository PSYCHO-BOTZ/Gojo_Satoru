import time

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.enums import ChatType as CT
from pyrogram.errors import RPCError
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup, Message)

from Powers import SUPPORT_STAFF
from Powers.bot_class import Gojo
from Powers.database.approve_db import Approve
from Powers.database.flood_db import Floods
from Powers.utils.custom_filters import admin_filter, command
from Powers.utils.kbhelpers import ikb

Flood = Floods()

approve = Approve()

on_key = ["on", "start", "disable"]
off_key = ["off", "end", "enable", "stop"]

close_kb =InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "Close ❌",
                callback_data="close"
            )
        ]
    ]
)

action_kb = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "Mute 🔇",
                callback_data="mute"
            ),
            InlineKeyboardButton(
                "Ban 🚷",
                callback_data="ban"
            ),
            InlineKeyboardButton(
                "Kick",
                callback_data="kick"
            )
        ]
    ]
)

within_kb = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "5",
                callback_data="5"
            ),
            InlineKeyboardButton(
                "10",
                callback_data="10"
            ),
            InlineKeyboardButton(
                "15",
                callback_data="15"
            )
        ]
    ]
)

limit_kb = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "5",
                callback_data="l_5"
            ),
            InlineKeyboardButton(
                "10",
                callback_data="l_10"
            ),
            InlineKeyboardButton(
                "15",
                callback_data="l_15"
            )
        ]
    ]
)

@Gojo.on_message(command(['floodaction','actionflood']))
async def flood_action(c: Gojo, m: Message):
    if m.chat.type == CT.PRIVATE:
        await m.reply_text("Use this command in group")
        return
    c_id = m.chat.id
    is_flood = Flood.is_chat(c_id)
    saction = is_flood[2]
    if is_flood:
        await m.reply_text(
            f"Choose a action given bellow to do when flood happens.\n **CURRENT ACTION** is {saction}",
            reply_markup=action_kb
        )
        return
    await m.reply_text("Switch on the flood protection first.")
    return

@Gojo.on_message(command(['setflood', 'flood']) & ~filters.bot & admin_filter)
async def flood_set(c: Gojo, m: Message):
    if m.chat.type == CT.PRIVATE:
        return await m.reply_text("This command is ment to be used in groups.")
    split = m.text.split(None, 1)
    c_id = m.chat.id
    is_flood = Flood.is_chat(c_id)
    if len(split) == 1:
        c_id = m.chat.id
        if is_flood:
            saction = is_flood[2]
            slimit = is_flood[0]
            swithin = is_flood[1]
            return await m.reply_text(f"Flood is on for this chat\n**Action**:{saction}\n**Messages**:{slimit} within {swithin} sec")
        return await m.reply_text("Flood protection is off of this chat.")
    
    if len(split) == 2:
        c_id = m.chat.id
        if split[1].lower() in on_key:
            Flood.save_flood(m.chat.id, 5, 5, 'mute')
            await m.reply_text("Flood protection has been started for this group.")
            return
        if split[1].lower() in off_key:
            Flood.rm_flood(m.chat.id, slimit, swithin, saction)
            await m.reply_text("Flood protection has been stopped for this chat")
            return
    await m.reply_text("**Usage:**\n `/setflood on/off`")
    return

@Gojo.on_callback_query()
async def callbacks(c: Gojo, q: CallbackQuery):
    data = q.data
    if data == "close":
        await q.message.delete()
        q.answer("Closed")
        return
    c_id = q.message.chat.id
    is_flood = Flood.is_chat(c_id)
    saction = is_flood[2]
    slimit = is_flood[0]
    swithin = is_flood[1]
    user = q.from_user.id
    user_status = (await q.message.chat.get_member(q.from_user.id)).status
    if user in SUPPORT_STAFF or user_status in [CMS.OWNER, CMS.ADMINISTRATOR]:
        if data in ["mute", "ban", "kick"]:
            Flood.save_flood(c_id, slimit, swithin, data)
            await q.answer("Updated action", show_alert=True)
            q.edit_message_caption(
                f"Set the limit of message after the flood protection will be activated\n **CURRENT LIMIT** {slimit} messages",
                reply_markup=limit_kb
            )
            return
        if data in ["l_5", "l_10", "l_15"]:
            change = int(data.split("_")[1])
            Flood.save_flood(c_id, change, swithin, saction)
            await q.answer("Updated limit", show_alert=True)
            q.edit_message_caption(
                f"Set the time with the number of message recived treated as flood\n **CUURENT TIME** {swithin}",
                reply_markup=within_kb
            )
            return
        if data in ["5", "10", "15"]:
            change = int(data)
            Flood.save_flood(c_id, slimit, change, saction)
            await q.answer("Updated", show_alert=True)
            q.edit_message_caption(
                "Flood protection setting has been updated",
                reply_markup=close_kb
            )
            return
    else:
        await q.answer(
            "You don't have enough permission to do this!\nStay in your limits!",
            show_alert=True,
            )

@Gojo.on_callback_query(filters.regex("^un_"))
async def reverse_callbacks(c: Gojo, q: CallbackQuery):
    data = q.data.split("_")
    action = data[1]
    user_id = int(data[2])
    if action == "ban":
        user = await q.message.chat.get_member(q.from_user.id)
        if not user.privileges.can_restrict_members and q.from_user.id in SUPPORT_STAFF:
            await q.answer(
                "You don't have enough permission to do this!\nStay in your limits!",
                show_alert=True,
            )
            return
        whoo = await c.get_chat(user_id)
        doneto = whoo.first_name if whoo.first_name else whoo.title
        try:
            await q.message.chat.unban_member(user_id)
        except RPCError as e:
            await q.message.edit_text(f"Error: {e}")
            return
        await q.message.edit_text(f"{q.from_user.mention} unbanned {doneto}!")
        return

    if action == "mute":
        user = await q.message.chat.get_member(q.from_user.id)

        if not user.privileges.can_restrict_members and user.id in SUPPORT_STAFF:
            await q.answer(
                "You don't have enough permission to do this!\nStay in your limits!",
                show_alert=True,
            )
            return
        whoo = await c.get_users(user_id)
        try:
            await q.message.chat.unban_member(user_id)
        except RPCError as e:
            await q.message.edit_text(f"Error: {e}")
            return
        await q.message.edit_text(f"{q.from_user.mention} unmuted {whoo.mention}!")
        return

@Gojo.on_message(filters.all & ~filters.bot, ~filters.private, 10)
async def flood_watcher(c: Gojo, m: Message):
    c_id = m.chat.id
    u_id = m.from_user.id
    is_flood = Flood.is_chat(c_id)
    app_users = Approve(m.chat.id).list_approved()
    if u_id in {i[0] for i in app_users}:
        return #return if the user is approved
    if not is_flood or u_id in SUPPORT_STAFF:
        return #return if the user is in support_staff
    user_status = (await m.chat.get_member(m.from_user.id)).status
    if user_status in [CMS.OWNER, CMS.ADMINISTRATOR]:
        return #return if the user is owner or admin
    action = is_flood[2]
    limit = int(is_flood[0])
    within = int(is_flood[1])
    dic = {}
    for i in str(dic.keys()):
        if str(c_id) != i:
            z = {c_id : set()}
            dic.update(z)
    dic[c_id].add(u_id)
    # to be continued